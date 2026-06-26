# GRU953 Markdown

**A standalone Windows desktop app by GRU953 that converts documents, images, and spreadsheets to clean Markdown — with one-click smart OCR and Bengali (Bijoy → Unicode) support.**

[![Release](https://img.shields.io/github/v/release/GRU-953/gru953-markdown?style=flat-square&color=0A6E5C)](https://github.com/GRU-953/gru953-markdown/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/GRU-953/gru953-markdown/ci.yml?branch=master&style=flat-square&label=CI)](https://github.com/GRU-953/gru953-markdown/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-145%20passing-brightgreen?style=flat-square)](https://github.com/GRU-953/gru953-markdown/actions/workflows/ci.yml)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue?style=flat-square&logo=windows)](https://github.com/GRU-953/gru953-markdown/releases/latest)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![GRU953](https://img.shields.io/badge/GRU953-Open%20Tech-0A6E5C?style=flat-square)](https://github.com/GRU-953)

> Simple technology. For everyone.
> <span lang="bn">সহজ প্রযুক্তি। সবার জন্য।</span>

---

## Download

> **[→ Download GRU953Markdown.exe](https://github.com/GRU-953/gru953-markdown/releases/latest)**

No Python installation. No setup wizard. Just download and run.

| | |
|---|---|
| **OS** | Windows 10 / 11 (64-bit) |
| **Runtime** | Microsoft Edge WebView2 (ships with Windows 11; auto-installed on Win 10) |
| **First launch** | Allow 5–10 seconds — the bundle extracts itself once |

---

## Features

### One-click smart conversion

A single **Convert** button transparently chains everything a file needs:

```
file ─▶ MarkItDown (documents)  ┐
        or Tesseract OCR (images) ┴─▶ auto-detect Bijoy ─▶ Unicode Bengali ─▶ Markdown
```

- **Documents** — PDF, Word (.docx, .doc legacy), Excel (.xlsx, .xls), PowerPoint (.pptx), HTML, CSV, JSON, XML, ZIP, RTF, audio
- **Images** — PNG/JPG/TIFF/BMP/WEBP/GIF are **automatically OCR'd** (no separate step)
- **Bengali** — if the result is Bijoy/SutonnyMJ encoded, it is **automatically converted to Unicode**
- Each file shows which steps ran (e.g. MarkItDown · Bijoy→Unicode, or PDF OCR · Bijoy→Unicode)
- Files that convert but contain no text receive an amber ⚠ badge instead of a green tick

### Batch file queue

- Drag-and-drop or browse; **drag to reorder**
- Per-file status with live progress and a **Retry failed** action
- Convert all in one click

### Markdown editor + live preview

- Toggle between a rendered **Preview** and an editable **Markdown** view
- Bengali text is rendered with proper Unicode fonts
- **Copy**, **Export** (`.md` / `.html` / `.txt`), or **Export all** combined into one document

### Three GRU953 brand themes

**GRU953 Teal** · **GRU953 Indigo** · **GRU953 Amber** — each in **light and dark** mode, switchable
live in Settings. Your choice is remembered. All colours drawn from the GRU953 Open Spectrum palette.

### Dedicated OCR & Bijoy tools

Standalone **OCR** (English / বাংলা / Both) and **Bijoy → Unicode** views remain available for
direct text work, with automatic script detection.

### Conversion history

Every conversion is logged with a timestamp and the steps applied — browse or clear it anytime.

---

## Architecture

v4 separates a thin Python backend from an HTML/CSS/JS frontend rendered in a native
WebView2 window via [pywebview](https://pywebview.flowrl.com/):

```
┌─────────────────────────────┐     window.pywebview.api      ┌──────────────────────┐
│  Frontend (web/)            │ ◀───────────────────────────▶ │  Python backend       │
│  index.html · CSS · app.js  │     JSON bridge (js_api)      │  app.py (Api) →       │
│  marked.js · Tabler icons   │                               │  pipeline · ocr ·     │
└─────────────────────────────┘                               │  bijoy · settings     │
                                                              └──────────────────────┘
```

The pure-Python logic modules (`pipeline`, `bijoy_unicode`, `ocr_engine`, `settings`,
`utils`) carry **100% test coverage** and have no GUI dependencies.

---

## Build from source

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11 – 3.13 | Python 3.14 works but requires `--console` (see notes) |
| [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) | evergreen | Pre-installed on Windows 11 |
| [Tesseract OCR v5](https://github.com/UB-Mannheim/tesseract/wiki) | 5.x | Install to `C:\Program Files\Tesseract-OCR\`; add `eng` + `ben` traineddata |
| PyInstaller | 6.x | `pip install pyinstaller` |

### Steps

```bash
git clone https://github.com/GRU-953/gru953-markdown.git
cd gru953-markdown
pip install -r requirements.txt

# Run directly (development)
python app.py

# Build standalone .exe
build_exe.bat
```

The compiled exe is written to `dist\GRU953Markdown.exe`.

### PyInstaller notes

- `--collect-all webview` is required — it bundles pywebview's JS bridge and the
  WebView2 (`edgechromium`) backend assemblies loaded via `pythonnet`/`clr_loader`.
- `--add-data "web;web"` ships the HTML/CSS/JS frontend (including the bundled
  `marked.min.js`, so Markdown preview works fully offline).
- `--collect-all magika` is required — MarkItDown depends on magika ML models.
- Use `--console` (not `--windowed`) — the `runw.exe` bootloader hangs silently on
  Python 3.14 with `--onefile`. The console window is hidden programmatically at startup.

---

## Tests

```bash
pip install pytest pytest-cov
pytest tests/ --cov=bijoy_unicode --cov=ocr_engine --cov=utils --cov=settings --cov=pipeline
```

**145 tests** across all five logic modules. CI runs them on every push
(Python 3.11 + 3.12) and the release workflow runs them before building the exe.

---

## Project structure

```
gru953-markdown/
├── app.py                # pywebview entry — window + JS↔Python Api bridge
├── pipeline.py           # unified convert: MarkItDown → OCR → Bijoy
├── bijoy_unicode.py      # Bijoy / SutonnyMJ → Unicode (Mukti port)
├── ocr_engine.py         # Tesseract wrapper — bundle-aware path resolution
├── settings.py           # persistent JSON config (theme, palette, history…)
├── utils.py              # shared helpers
├── web/                  # frontend
│   ├── index.html
│   ├── css/{themes,styles}.css
│   └── js/{app.js, vendor/marked.min.js}
├── assets/               # fonts (OFL), app icon, brand mark
├── tests/                # pytest suite — 145 tests
├── build_exe.bat         # PyInstaller build script
└── .github/workflows/    # CI (pytest + coverage) and auto-release (exe on tag)
```

---

## Credits & attributions

| Component | Credit |
|---|---|
| [MarkItDown](https://github.com/microsoft/markitdown) | Microsoft — core document-to-Markdown engine |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | Google — bundled as `tesseract.exe` v5.x |
| [Mukti](https://github.com/Aninda-Howlader/bijoy-unicode) | Aninda Sundar Howlader — Bijoy→Unicode library (ported to Python) |
| [pywebview](https://github.com/r0x0r/pywebview) | Roman Sirokov — native webview windows for Python |
| [marked](https://github.com/markedjs/marked) | Markdown rendering in the preview |
| [Tabler Icons](https://github.com/tabler/tabler-icons) | MIT-licensed outline icon set |
| DM Sans | SIL Open Font License — English UI typeface |
| Noto Sans Bengali | SIL Open Font License — Bengali typeface |

---

## About GRU953

GRU953 is a not-for-profit, open-source product organisation on a mission to make technology
simple — and accessible — for all. Built openly with a global community and a home in Bangladesh,
GRU953 designs tools that anyone can use, study, and improve.

Simple technology. For everyone.

---

## License

MIT — see [LICENSE](LICENSE) for details.
