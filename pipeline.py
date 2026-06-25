"""
Unified conversion pipeline.

One entry point — convert_file() — that transparently chains the three
capabilities behind a single action:

    1. If the input is an image  -> Tesseract OCR  (ocr_engine)
       otherwise                 -> MarkItDown document conversion
    2. If the resulting text is Bijoy/SutonnyMJ encoded
       -> convert it to Unicode Bengali               (bijoy_unicode)

Every external dependency is injectable, so the whole pipeline is unit-testable
without MarkItDown, Tesseract, or any GUI.
"""

from pathlib import Path

from bijoy_unicode import convert_bijoy_to_unicode, is_bijoy
from ocr_engine import ocr_image

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif", ".webp"}

_mid = None


def _get_markitdown():
    """Lazily construct a shared MarkItDown instance."""
    global _mid
    if _mid is None:
        from markitdown import MarkItDown
        _mid = MarkItDown()
    return _mid


def is_image(path) -> bool:
    """Return True if *path* has a known raster-image extension."""
    return Path(path).suffix.lower() in IMAGE_EXTS


def convert_file(
    path,
    *,
    auto_ocr: bool = True,
    auto_bijoy: bool = True,
    ocr_lang: str = "English",
    markitdown=None,
    ocr_func=None,
    is_bijoy_func=is_bijoy,
    bijoy_func=convert_bijoy_to_unicode,
) -> dict:
    """
    Convert a single file to Markdown/text, applying OCR and Bijoy→Unicode
    automatically when applicable.

    Returns a dict::

        {"text": str, "steps": ["ocr"|"markitdown", "bijoy"?]}

    Raises FileNotFoundError if the path does not exist; any converter error
    propagates to the caller (the Api layer turns it into a per-file status).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    steps = []

    if auto_ocr and is_image(p):
        runner = ocr_func or ocr_image
        text = runner(str(p), ocr_lang)
        steps.append("ocr")
    else:
        md = markitdown or _get_markitdown()
        result = md.convert(str(p))
        text = result.text_content or ""
        steps.append("markitdown")

    if auto_bijoy and text and is_bijoy_func(text):
        text = bijoy_func(text)
        steps.append("bijoy")

    return {"text": text, "steps": steps}
