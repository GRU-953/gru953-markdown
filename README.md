# MarkItDown Converter — GRU-953

A standalone Windows app that converts files to Markdown, runs OCR on images, and converts Bijoy-encoded Bengali text to Unicode — all in one place.

## Download

**[→ Download MarkItDownConverter.exe](https://github.com/GRU-953/markitdown-converter/releases/latest)**

No Python, no installation. Run the .exe directly on Windows 10/11 (64-bit).  
First launch extracts the bundle — allow 5–10 seconds before the window appears.

---

## Features

### Convert Files
Convert PDF, Word, Excel, PowerPoint, HTML, CSV, JSON, images, and ZIP archives to clean Markdown.

- Drag files into the drop zone or click **+ Add Files**
- Hit **Convert All** — each file shows a ✓ / ✗ status dot
- Click a file to see its Markdown in the **Raw MD** or **Preview** tab
- **Copy** to clipboard or **Save .md** to disk

### OCR
Extract text from images (PNG, JPG, TIFF, BMP) in English, বাংলা, or both.

- Drop an image or click to browse
- Choose language, then **Extract Text**
- Enable **Auto-convert Bijoy → Unicode** to instantly convert Bijoy-encoded OCR output

### Bijoy → Unicode
Convert SutonnyMJ / Bijoy-encoded Bengali text to proper Unicode.

- Paste Bijoy text into the input box — the script is detected automatically
- Click **Convert ↓** to get Unicode Bengali in the output box

---

## Build from source

```bash
git clone https://github.com/GRU-953/markitdown-converter.git
cd markitdown-converter
pip install -r requirements.txt
python converter.py          # run directly
build_exe.bat                # build standalone .exe (requires PyInstaller)
```

**Requirements:** Python 3.11+, [Tesseract OCR v5](https://github.com/UB-Mannheim/tesseract/wiki) at `C:\Program Files\Tesseract-OCR\` with `eng.traineddata` and `ben.traineddata`.

---

## Bijoy engine

The Bijoy → Unicode converter is a Python port of [Mukti](https://github.com/Aninda-Howlader/bijoy-unicode) — Aninda S Howlader's open-source JS conversion library — MIT licensed.

---

## Brand

UI palette, typography, and assets follow the **GRU-953** brand guidelines.  
Fonts: Figtree · Hind Siliguri · Tiro Bangla (all OFL licensed).
