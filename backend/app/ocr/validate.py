"""Safe file validation: magic bytes (not the client-supplied MIME), size cap, decodability, pixel-bomb guard."""
import hashlib
import io

from PIL import Image, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 40_000_000  # reject decompression bombs (Pillow raises DecompressionBombError above 2x)

ALLOWED = {"image/jpeg": (".jpg", ".jpeg"), "image/png": (".png",), "application/pdf": (".pdf",)}


class InvalidFile(ValueError):
    pass


def sniff_mime(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    return None  # DICOM etc. intentionally unsupported (no processing pipeline implemented)


def validate_upload(data: bytes, filename: str, max_bytes: int) -> dict:
    if not data:
        raise InvalidFile("Empty file.")
    if len(data) > max_bytes:
        raise InvalidFile(f"File exceeds the {max_bytes // (1024*1024)} MB limit.")
    mime = sniff_mime(data)
    if mime is None:
        raise InvalidFile("Unsupported file type. Allowed: JPG, PNG, PDF.")
    if not filename.lower().endswith(ALLOWED[mime]):
        raise InvalidFile("File extension does not match its content.")
    info: dict = {"mime_type": mime, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    if mime.startswith("image/"):
        try:
            with Image.open(io.BytesIO(data)) as im:
                im.verify()
            with Image.open(io.BytesIO(data)) as im:
                info.update(width=im.width, height=im.height, mode=im.mode, format=im.format)
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as e:
            raise InvalidFile(f"Corrupt or unsafe image ({type(e).__name__}).")
        if info["width"] < 100 or info["height"] < 100:
            raise InvalidFile("Image is too small to be a document (min 100x100).")
    else:
        from pypdf import PdfReader
        try:
            r = PdfReader(io.BytesIO(data))
            if r.is_encrypted:
                raise InvalidFile("Encrypted PDFs are not supported.")
            info["pages"] = len(r.pages)
        except InvalidFile:
            raise
        except Exception as e:
            raise InvalidFile(f"Corrupt PDF ({type(e).__name__}).")
        if info["pages"] > 20:
            raise InvalidFile("PDF has too many pages (max 20).")
    return info


def safe_filename(name: str) -> str:
    base = name.replace("\\", "/").split("/")[-1]
    cleaned = "".join(c if c.isalnum() or c in "._-" else "_" for c in base)[:100]
    return cleaned.lstrip(".") or "file"
