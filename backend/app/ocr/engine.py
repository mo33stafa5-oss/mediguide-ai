"""OCR: OpenCV pre-processing + Tesseract (pytesseract) with per-word confidence; PDF text layer via pypdf.
Tesseract is a system binary: it is NOT available on Vercel, so OCR runs in the Docker worker (Dockerfile.ocr)."""
import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field


@dataclass
class OcrResult:
    text: str
    mean_confidence: float | None          # 0..100 from Tesseract; None if text layer (digital PDF)
    engine: str
    warnings: list[str] = field(default_factory=list)
    low_conf_words: list[str] = field(default_factory=list)


def ocr_available() -> bool:
    try:
        import pytesseract  # noqa: F401
        import cv2  # noqa: F401
    except Exception:
        return False
    return shutil.which("tesseract") is not None


def preprocess(data: bytes):
    import cv2
    import numpy as np
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("undecodable image")
    h, w = img.shape
    if max(h, w) < 1600:  # upscale small photos: Tesseract works best around 300 DPI
        s = 1600 / max(h, w)
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    img = cv2.fastNlMeansDenoising(img, None, 10, 7, 21)
    return cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)


def _tesseract_langs() -> str:
    import pytesseract
    have = set(pytesseract.get_languages())
    return "+".join(l for l in ("eng", "ara") if l in have) or "eng"


def ocr_image(data: bytes) -> OcrResult:
    import pytesseract
    from pytesseract import Output
    if not ocr_available():
        raise RuntimeError("Tesseract is not installed")
    img = preprocess(data)
    d = pytesseract.image_to_data(img, lang=_tesseract_langs(), config="--psm 6", output_type=Output.DICT)
    words, confs, low = [], [], []
    lines: dict[tuple, list[str]] = {}
    for i, w in enumerate(d["text"]):
        w = w.strip()
        c = float(d["conf"][i])
        if not w or c < 0:
            continue
        confs.append(c)
        lines.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append(w)
        if c < 60:
            low.append(w)
    text = "\n".join(" ".join(ws) for ws in lines.values())
    mean = round(sum(confs) / len(confs), 1) if confs else 0.0
    warns = []
    if not text.strip():
        warns.append("No readable text detected.")
    elif mean < 60:
        warns.append(f"Low OCR confidence ({mean}/100): results may be wrong; please verify manually.")
    return OcrResult(text, mean, "tesseract+opencv", warns, low[:50])


def ocr_pdf(data: bytes) -> OcrResult:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    text = "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    if len(text) > 30:
        return OcrResult(text, None, "pypdf-text-layer", [])
    # scanned PDF: rasterise with poppler's pdftoppm, then OCR each page
    if not shutil.which("pdftoppm"):
        return OcrResult("", None, "none", ["Scanned PDF without text layer and poppler is not installed; upload a JPG/PNG instead."])
    with tempfile.TemporaryDirectory() as td:
        src = f"{td}/in.pdf"
        open(src, "wb").write(data)
        subprocess.run(["pdftoppm", "-r", "200", "-png", "-l", "5", src, f"{td}/p"], check=True, timeout=60)
        import glob
        parts = [ocr_image(open(p, "rb").read()) for p in sorted(glob.glob(f"{td}/p*.png"))]
    if not parts:
        return OcrResult("", None, "none", ["PDF could not be rasterised."])
    confs = [p.mean_confidence for p in parts if p.mean_confidence is not None]
    return OcrResult("\n".join(p.text for p in parts), round(sum(confs) / len(confs), 1) if confs else None,
                     "pdftoppm+tesseract", [w for p in parts for w in p.warnings], [w for p in parts for w in p.low_conf_words][:50])


def extract_text(data: bytes, mime: str) -> OcrResult:
    return ocr_pdf(data) if mime == "application/pdf" else ocr_image(data)


def extract_text_remote(data: bytes, mime: str, url: str, token: str) -> OcrResult:
    """Delegate OCR to the Docker worker (Tesseract is unavailable on Vercel). Same code, different runtime."""
    import httpx
    r = httpx.post(url.rstrip("/") + "/internal/ocr", headers={"X-Worker-Token": token}, files={"file": ("doc", data, mime)}, timeout=120)
    r.raise_for_status()
    j = r.json()
    return OcrResult(j["text"], j["mean_confidence"], j["engine"] + "@worker", j["warnings"], j["low_conf_words"])
