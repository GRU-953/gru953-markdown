"""
Full corpus audit — every file in D:/Test_files tested against the live pipeline.

Each slot keeps one persistent worker subprocess alive across many files,
amortising the 8-15 s MarkItDown/magika startup cost to once per worker
lifetime instead of once per file.  Defaults are tuned for 2 GB RAM:
  --workers 1        one ONNX model load (~500 MB) instead of N concurrent ones
  --file-timeout 120 enough for large PDFs/ZIPs without false timeouts
  --skip-large 200   skip >200 MB files that would OOM on low-end machines

Usage:
    python full_corpus_audit.py [--no-ocr] [--workers N] [--out results.json]
                                [--file-timeout N] [--skip-large MB]
"""
import sys, io, json, time, pathlib, argparse, subprocess, threading, queue
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TEST_ROOT = pathlib.Path("D:/Test_files")
SKIP_NAME_PREFIXES = ("~$", "._", ".~")
SKIP_EXTS = {".tmp", ".ds_store", ".lnk", ".bak", ""}

# Persistent worker script — stays alive reading JSON lines from stdin and
# writing JSON lines to stdout.  Magika ONNX loads once, not once per file.
_WORKER_CODE = """\
import sys, json, time, pathlib
proj = sys.argv[1]
sys.path.insert(0, proj)
from pipeline import convert_file
sys.stderr.write("WORKER_READY\\n")
sys.stderr.flush()
for raw in sys.stdin:
    raw = raw.strip()
    if not raw or raw == "STOP":
        break
    t0 = time.time()
    ext = ""
    kb = 0.0
    path_str = "?"
    try:
        req = json.loads(raw)
        path_str = req["path"]
        auto_ocr = req.get("auto_ocr", False)
        p = pathlib.Path(path_str)
        ext = p.suffix.lower()
        kb = round(p.stat().st_size / 1024, 1) if p.exists() else 0.0
        r = convert_file(path_str, auto_ocr=auto_ocr, auto_bijoy=True)
        txt = r.get("text", "")
        words = len(txt.split()) if txt else 0
        status = "PASS" if words > 0 else "EMPTY"
        result = {"status": status, "ext": ext, "kb": kb,
                  "elapsed": round(time.time() - t0, 2), "words": words,
                  "steps": r.get("steps", []), "file": path_str,
                  "name": p.name, "error": ""}
    except MemoryError as exc:
        result = {"status": "FAIL", "ext": ext, "kb": kb,
                  "elapsed": round(time.time() - t0, 2), "words": 0,
                  "steps": [], "file": path_str,
                  "name": pathlib.Path(path_str).name,
                  "error": "MemoryError: " + str(exc)[:200]}
    except Exception as exc:
        msg = str(exc)
        s = ("UNSUPPORTED" if "unsupported format" in msg.lower() or
             "no text can be extracted" in msg.lower() else "FAIL")
        result = {"status": s, "ext": ext, "kb": kb,
                  "elapsed": round(time.time() - t0, 2), "words": 0,
                  "steps": [], "file": path_str,
                  "name": pathlib.Path(path_str).name, "error": msg[:300]}
    print(json.dumps(result), flush=True)
"""


def _file_timeout(size_bytes: int, base: int) -> int:
    """Base timeout + 1 extra second per MB beyond the first megabyte."""
    extra = max(0, int(size_bytes / (1024 * 1024)) - 1)
    return base + extra


class WorkerSubprocess:
    """One persistent subprocess that processes files sequentially via stdin/stdout."""
    STARTUP_TIMEOUT = 60

    def __init__(self, proj_path: str):
        self.alive = False
        self._proc = subprocess.Popen(
            [sys.executable, "-c", _WORKER_CODE, proj_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )
        self._ready_event = threading.Event()
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()
        if self._ready_event.wait(timeout=self.STARTUP_TIMEOUT):
            self.alive = True
        else:
            try:
                self._proc.kill()
            except Exception:
                pass

    def _drain_stderr(self):
        try:
            for line in self._proc.stderr:
                if "WORKER_READY" in line:
                    self._ready_event.set()
        except Exception:
            pass

    def kill(self):
        self.alive = False
        try:
            self._proc.kill()
        except Exception:
            pass

    def process(self, path: str, auto_ocr: bool, timeout: int):
        """Send one file request; wait up to *timeout* seconds for the result.
        Returns (result_dict, None) on success or (None, error_str) on failure.
        """
        resp_q: "queue.Queue[str | None]" = queue.Queue()

        def _read():
            try:
                line = self._proc.stdout.readline()
                resp_q.put(line.strip() if line else "")
            except Exception:
                resp_q.put(None)

        try:
            self._proc.stdin.write(json.dumps({"path": path, "auto_ocr": auto_ocr}) + "\n")
            self._proc.stdin.flush()
        except Exception as exc:
            self.alive = False
            return None, f"stdin write failed: {exc}"

        reader = threading.Thread(target=_read, daemon=True)
        reader.start()
        reader.join(timeout=timeout)

        if reader.is_alive():
            self.kill()
            return None, f"Timeout after {timeout}s"

        try:
            data = resp_q.get_nowait()
        except queue.Empty:
            self.alive = False
            return None, "No response from worker"

        if data is None or data == "":
            self.alive = False
            return None, "Worker stdout closed (crashed)"

        try:
            return json.loads(data), None
        except json.JSONDecodeError:
            self.alive = False
            return None, f"Bad JSON from worker: {data[:80]}"


_print_lock = threading.Lock()
_last_report_time = [0.0]


def _progress(done: int, total: int, t_start: float) -> None:
    now = time.time()
    if done == total or done % 50 == 0 or (now - _last_report_time[0]) >= 30:
        with _print_lock:
            now2 = time.time()
            if done == total or done % 50 == 0 or (now2 - _last_report_time[0]) >= 30:
                elapsed = round(now2 - t_start, 1)
                rate = done / elapsed if elapsed > 0 else 0
                eta = round((total - done) / rate) if rate > 0 else 0
                print(f"  [{done}/{total}] {elapsed}s elapsed  rate={rate:.2f}/s  "
                      f"ETA={eta}s …", flush=True)
                _last_report_time[0] = now2


def _worker_slot(
    file_q: "queue.Queue",
    results: list,
    results_lock: threading.Lock,
    proj: str,
    base_timeout: int,
    skip_large_mb: int,
    counter: list,
    total: int,
    t_start: float,
) -> None:
    MAX_RESTARTS = 5
    restarts = 0
    worker = WorkerSubprocess(proj)

    while True:
        item = file_q.get()
        if item is None:
            file_q.task_done()
            break

        path, auto_ocr = item
        p = pathlib.Path(path)
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        ext = p.suffix.lower()
        kb = round(size / 1024, 1)

        if skip_large_mb and size > skip_large_mb * 1024 * 1024:
            r = {"status": "SKIPPED_LARGE", "ext": ext, "kb": kb, "elapsed": 0.0,
                 "steps": [], "words": 0, "file": path, "name": p.name,
                 "error": f"Skipped: >{skip_large_mb} MB"}
            with results_lock:
                results.append(r)
                counter[0] += 1
                done_count = counter[0]
            _progress(done_count, total, t_start)
            file_q.task_done()
            continue

        timeout = _file_timeout(size, base_timeout)

        if not worker.alive:
            if restarts >= MAX_RESTARTS:
                r = {"status": "FAIL", "ext": ext, "kb": kb, "elapsed": 0.0,
                     "steps": [], "words": 0, "file": path, "name": p.name,
                     "error": f"Worker dead after {MAX_RESTARTS} restart attempts"}
                with results_lock:
                    results.append(r)
                    counter[0] += 1
                    done_count = counter[0]
                _progress(done_count, total, t_start)
                file_q.task_done()
                continue
            restarts += 1
            with _print_lock:
                print(f"  [restart {restarts}/{MAX_RESTARTS}] spawning new worker …",
                      flush=True)
            worker = WorkerSubprocess(proj)
            if not worker.alive:
                r = {"status": "FAIL", "ext": ext, "kb": kb, "elapsed": 0.0,
                     "steps": [], "words": 0, "file": path, "name": p.name,
                     "error": "New worker failed to start within 60 s"}
                with results_lock:
                    results.append(r)
                    counter[0] += 1
                    done_count = counter[0]
                _progress(done_count, total, t_start)
                file_q.task_done()
                continue

        result, err = worker.process(path, auto_ocr, timeout)

        if result is not None:
            r = result
            restarts = 0
        else:
            elapsed_val = float(timeout) if "Timeout" in (err or "") else 0.0
            r = {"status": "FAIL", "ext": ext, "kb": kb, "elapsed": elapsed_val,
                 "steps": [], "words": 0, "file": path, "name": p.name,
                 "error": err or "Unknown error"}

        with results_lock:
            results.append(r)
            counter[0] += 1
            done_count = counter[0]
        _progress(done_count, total, t_start)
        file_q.task_done()

    worker.kill()


def main():
    ap = argparse.ArgumentParser(description="Full corpus audit against the live pipeline.")
    ap.add_argument("--no-ocr", action="store_true",
                    help="Disable OCR (faster; tests text extraction only)")
    ap.add_argument("--workers", type=int, default=1,
                    help="Persistent worker subprocesses (default 1 — safe for 2 GB RAM)")
    ap.add_argument("--out", default="full_audit_results.json",
                    help="Output JSON path")
    ap.add_argument("--file-timeout", type=int, default=120,
                    help="Base per-file timeout in seconds; scales +1s/MB (default 120)")
    ap.add_argument("--skip-large", type=int, default=200,
                    help="Skip files > N MB; 0 = no limit (default 200)")
    args = ap.parse_args()

    auto_ocr = not args.no_ocr
    proj_dir = str(pathlib.Path(__file__).parent)

    all_files = []
    for f in TEST_ROOT.rglob("*"):
        if not f.is_file():
            continue
        if any(f.name.startswith(pref) for pref in SKIP_NAME_PREFIXES):
            continue
        if f.suffix.lower() in SKIP_EXTS or f.name.lower() in (".ds_store",):
            continue
        all_files.append(str(f))
    all_files.sort()

    total = len(all_files)
    print(f"\nFull corpus audit — {total} files, {args.workers} worker(s), "
          f"ocr={'on' if auto_ocr else 'off'}, base-timeout={args.file_timeout}s")
    if args.skip_large:
        print(f"  Skipping files > {args.skip_large} MB")
    print(f"  Persistent workers: magika ONNX loads once per slot, not once per file")
    print("=" * 80)

    file_q: "queue.Queue" = queue.Queue()
    for f in all_files:
        file_q.put((f, auto_ocr))
    for _ in range(args.workers):
        file_q.put(None)

    results: list = []
    results_lock = threading.Lock()
    counter = [0]
    t_start = time.time()

    threads = [
        threading.Thread(
            target=_worker_slot,
            args=(file_q, results, results_lock, proj_dir,
                  args.file_timeout, args.skip_large, counter, total, t_start),
            daemon=True,
        )
        for _ in range(args.workers)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    out_path = pathlib.Path(args.out)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    by_status: dict = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)

    print(f"\n{'Status':<16} {'Count':>6}  {'Ext distribution (top 8)'}")
    print("-" * 80)
    for st in ("PASS", "EMPTY", "UNSUPPORTED", "SKIPPED_LARGE", "FAIL"):
        group = by_status.get(st, [])
        if not group:
            continue
        top = Counter(r["ext"] for r in group).most_common(8)
        ext_str = "  ".join(f"{e}×{c}" for e, c in top)
        print(f"{st:<16} {len(group):>6}  {ext_str}")

    fails = by_status.get("FAIL", [])
    if fails:
        print(f"\nFAIL detail ({len(fails)} files):")
        err_groups: dict = {}
        for r in fails:
            key = r["error"][:80]
            err_groups.setdefault(key, []).append(r["ext"])
        for msg, exts in sorted(err_groups.items(), key=lambda x: -len(x[1])):
            cnt_by_ext = Counter(exts)
            print(f"  [{len(exts)}]  {msg[:70]}")
            print(f"        {dict(cnt_by_ext)}")

    empties = by_status.get("EMPTY", [])
    if empties:
        print(f"\nEMPTY ({len(empties)} — converted but yielded no text):")
        for ext, cnt in Counter(r["ext"] for r in empties).most_common():
            print(f"  {ext}: {cnt}")

    skipped = by_status.get("SKIPPED_LARGE", [])
    if skipped:
        print(f"\nSKIPPED_LARGE ({len(skipped)} files):")
        for r in skipped:
            mb = round(r["kb"] / 1024, 1)
            print(f"  {r['name']} ({mb} MB)")

    total_time = round(time.time() - t_start, 1)
    pass_c = len(by_status.get("PASS", []))
    empty_c = len(by_status.get("EMPTY", []))
    unsup_c = len(by_status.get("UNSUPPORTED", []))
    fail_c = len(by_status.get("FAIL", []))
    skip_c = len(by_status.get("SKIPPED_LARGE", []))
    fixable = pass_c + empty_c + fail_c
    print(f"\nSUMMARY: {pass_c} PASS  |  {empty_c} EMPTY  |  {unsup_c} UNSUPPORTED  "
          f"|  {fail_c} FAIL  |  {skip_c} SKIPPED")
    print(f"Fixable pass rate: {pass_c}/{fixable} = {100*pass_c//max(fixable,1)}%")
    print(f"Total time: {total_time}s  |  Results: {out_path}")
    sys.exit(0 if fail_c == 0 else 1)


if __name__ == "__main__":
    main()
