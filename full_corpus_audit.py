"""
Full corpus audit — every file in D:/Test_files tested against the live pipeline.

Each file is tested in its own subprocess so timeouts are fully enforced (thread
timeouts cannot interrupt a blocked MarkItDown / zipfile call).  Per-file timeout
scales with file size so large-but-legitimate files are given enough time.

Usage:
    python full_corpus_audit.py [--no-ocr] [--workers N] [--out results.json]
                                [--file-timeout N]  [--skip-large MB]
"""
import sys, os, io, json, time, pathlib, argparse, subprocess
import concurrent.futures
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TEST_ROOT = pathlib.Path("D:/Test_files")
SKIP_NAME_PREFIXES = ("~$", "._", ".~")
SKIP_EXTS = {".tmp", ".ds_store", ".lnk", ".bak", ""}

# Inline worker — injected into each subprocess via `python -c "..."`.
# Using {proj!r} and double-braces so .format() works with the f-string-like
# template without needing a raw string for the whole block.
_WORKER_TMPL = (
    "import sys,json,time,pathlib\n"
    "sys.path.insert(0,{proj!r})\n"
    "from pipeline import convert_file,is_unsupported\n"
    "p=pathlib.Path(sys.argv[1])\n"
    "ext=p.suffix.lower(); kb=round(p.stat().st_size/1024,1)\n"
    "auto_ocr=(sys.argv[2]=='1'); t0=time.time()\n"
    "try:\n"
    "    r=convert_file(str(p),auto_ocr=auto_ocr,auto_bijoy=True)\n"
    "    txt=r.get('text',''); words=len(txt.split()) if txt else 0\n"
    "    elapsed=round(time.time()-t0,2)\n"
    "    status='PASS' if words>0 else 'EMPTY'\n"
    "    print(json.dumps({{'status':status,'ext':ext,'kb':kb,'elapsed':elapsed,"
    "                       'steps':r.get('steps',[]),'words':words,"
    "                       'file':str(p),'name':p.name,'error':''}}))\n"
    "except ValueError as exc:\n"
    "    msg=str(exc)\n"
    "    s='UNSUPPORTED' if 'unsupported format' in msg.lower() or 'no text' in msg.lower() else 'FAIL'\n"
    "    print(json.dumps({{'status':s,'ext':ext,'kb':kb,'elapsed':round(time.time()-t0,2),"
    "                       'steps':[],'words':0,'file':str(p),'name':p.name,'error':msg}}))\n"
    "except Exception as exc:\n"
    "    print(json.dumps({{'status':'FAIL','ext':ext,'kb':kb,'elapsed':round(time.time()-t0,2),"
    "                       'steps':[],'words':0,'file':str(p),'name':p.name,'error':str(exc)[:200]}}))\n"
)


def _file_timeout(size_bytes: int, base: int) -> int:
    """1 extra second per MB beyond 1 MB, minimum = base."""
    extra = max(0, int(size_bytes / (1024 * 1024)) - 1)
    return base + extra


def _run_one(args):
    path, auto_ocr, worker_code, base_timeout, skip_large_mb = args
    p = pathlib.Path(path)
    size = p.stat().st_size
    ext = p.suffix.lower()
    kb = round(size / 1024, 1)

    if skip_large_mb and size > skip_large_mb * 1024 * 1024:
        return {"status": "SKIPPED_LARGE", "ext": ext, "kb": kb, "elapsed": 0.0,
                "steps": [], "words": 0, "file": path, "name": p.name,
                "error": f"Skipped: >{skip_large_mb} MB"}

    timeout = _file_timeout(size, base_timeout)
    t0 = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "-c", worker_code, path, "1" if auto_ocr else "0"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
        elapsed = round(time.time() - t0, 2)
        if result.returncode == 0 and result.stdout.strip():
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                pass
        stderr_tail = result.stderr.strip()[-200:] if result.stderr else ""
        return {"status": "FAIL", "ext": ext, "kb": kb, "elapsed": elapsed,
                "steps": [], "words": 0, "file": path, "name": p.name,
                "error": f"Worker exit {result.returncode}: {stderr_tail}"}
    except subprocess.TimeoutExpired:
        return {"status": "FAIL", "ext": ext, "kb": kb, "elapsed": timeout,
                "steps": [], "words": 0, "file": path, "name": p.name,
                "error": f"Timeout after {timeout}s"}
    except Exception as exc:
        return {"status": "FAIL", "ext": ext, "kb": kb,
                "elapsed": round(time.time() - t0, 2),
                "steps": [], "words": 0, "file": path, "name": p.name,
                "error": f"Unhandled: {exc}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="full_audit_results.json")
    ap.add_argument("--file-timeout", type=int, default=30,
                    help="Base per-file timeout (scales up 1s/MB for large files)")
    ap.add_argument("--skip-large", type=int, default=0,
                    help="Skip files > N MB (0 = no limit)")
    args = ap.parse_args()

    auto_ocr = not args.no_ocr
    proj_dir = str(pathlib.Path(__file__).parent)
    worker_code = _WORKER_TMPL.format(proj=proj_dir)

    all_files = []
    for f in TEST_ROOT.rglob("*"):
        if not f.is_file():
            continue
        if any(f.name.startswith(p) for p in SKIP_NAME_PREFIXES):
            continue
        if f.suffix.lower() in SKIP_EXTS or f.name.lower() in (".ds_store",):
            continue
        all_files.append(str(f))

    total = len(all_files)
    print(f"\nFull corpus audit — {total} files, {args.workers} workers, "
          f"ocr={'on' if auto_ocr else 'off'}, base-timeout={args.file_timeout}s")
    if args.skip_large:
        print(f"  Skipping files > {args.skip_large} MB")
    print("=" * 80)

    work_args = [(f, auto_ocr, worker_code, args.file_timeout, args.skip_large)
                 for f in all_files]

    results = []
    done = 0
    t_start = time.time()
    last_report = 0.0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for r in pool.map(_run_one, work_args, chunksize=1):
            results.append(r)
            done += 1
            now = time.time()
            if done == total or done % 50 == 0 or (now - last_report) >= 30:
                elapsed = round(now - t_start, 1)
                rate = done / elapsed if elapsed > 0 else 0
                eta = round((total - done) / rate) if rate > 0 else 0
                print(f"  [{done}/{total}] {elapsed}s elapsed  rate={rate:.1f}/s  "
                      f"ETA={eta}s …", flush=True)
                last_report = now

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
        print(f"\nEMPTY ({len(empties)} — converted but no text):")
        for ext, cnt in Counter(r["ext"] for r in empties).most_common():
            print(f"  {ext}: {cnt}")

    skipped = by_status.get("SKIPPED_LARGE", [])
    if skipped:
        print(f"\nSKIPPED_LARGE ({len(skipped)} files):")
        for r in skipped:
            print(f"  {r['name']} ({r['kb']//1024:.0f} MB)")

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
