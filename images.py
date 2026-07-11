"""Image processing for uploads — Pillow only, so it runs on any host.

Mirrors the original hand-tuned recipe: open -> fix orientation -> downscale to a
max edge -> save optimized JPEG. Plates max 1900px q84, hero max 2200px q84,
landing/cards smaller. Everything is written into /uploads as .jpg.
"""
import os
import uuid
from PIL import Image, ImageOps, UnidentifiedImageError

# Guard against decompression-bomb DoS: refuse absurdly large pixel dimensions.
# ~120 MP comfortably covers a 14k-wide panorama but rejects malicious files.
Image.MAX_IMAGE_PIXELS = 120_000_000

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.environ.get("FN_UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff"}


def _save_optimized(img, out_path, max_edge, quality):
    img = ImageOps.exif_transpose(img)          # honour camera rotation
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((max_edge, max_edge), Image.LANCZOS)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "JPEG", quality=quality, optimize=True, progressive=True)


def process_upload(file_storage, essay_id, role="plate"):
    """Save an uploaded werkzeug FileStorage as an optimized JPEG.

    Returns the path relative to UPLOAD_DIR (e.g. "essay_3/ab12cd.jpg"), which is
    what we store in the DB and serve under /uploads/<that>.
    """
    ext = os.path.splitext(file_storage.filename or "")[1].lower()
    if ext and ext not in ALLOWED_EXT:
        raise ValueError(f"unsupported file type: {ext}")

    sizes = {
        "plate": (1900, 84),
        "hero": (2200, 84),
        "card": (1200, 82),
    }
    max_edge, quality = sizes.get(role, sizes["plate"])

    rel_dir = f"essay_{essay_id}"
    name = f"{role}_{uuid.uuid4().hex[:10]}.jpg"
    rel_path = f"{rel_dir}/{name}"
    out_path = os.path.join(UPLOAD_DIR, rel_dir, name)

    try:
        with Image.open(file_storage.stream) as img:
            img.verify()                       # detect truncated/forged files
        file_storage.stream.seek(0)
        with Image.open(file_storage.stream) as img:
            _save_optimized(img, out_path, max_edge, quality)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise ValueError("ไฟล์นี้ไม่ใช่รูปภาพที่ใช้ได้ หรือเสียหาย")
    return rel_path


def process_site_upload(file_storage, role="hero"):
    """Save a landing-page image (hero / about portrait) into uploads/site/."""
    ext = os.path.splitext(file_storage.filename or "")[1].lower()
    if ext and ext not in ALLOWED_EXT:
        raise ValueError(f"unsupported file type: {ext}")
    sizes = {"hero": (2200, 84), "card": (1400, 82)}
    max_edge, quality = sizes.get(role, sizes["hero"])
    name = f"{role}_{uuid.uuid4().hex[:10]}.jpg"
    rel_path = f"site/{name}"
    out_path = os.path.join(UPLOAD_DIR, "site", name)
    try:
        with Image.open(file_storage.stream) as img:
            img.verify()
        file_storage.stream.seek(0)
        with Image.open(file_storage.stream) as img:
            _save_optimized(img, out_path, max_edge, quality)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise ValueError("ไฟล์นี้ไม่ใช่รูปภาพที่ใช้ได้ หรือเสียหาย")
    return rel_path


def import_from_path(src_path, essay_id, role="plate", name=None):
    """Used by the seed script: optimize an existing file on disk into /uploads."""
    rel_dir = f"essay_{essay_id}"
    name = name or f"{role}_{uuid.uuid4().hex[:10]}.jpg"
    rel_path = f"{rel_dir}/{name}"
    out_path = os.path.join(UPLOAD_DIR, rel_dir, name)
    sizes = {"plate": (1900, 84), "hero": (2200, 84), "card": (1200, 82)}
    max_edge, quality = sizes.get(role, sizes["plate"])
    with Image.open(src_path) as img:
        _save_optimized(img, out_path, max_edge, quality)
    return rel_path


def delete_upload(rel_path):
    if not rel_path:
        return
    p = os.path.join(UPLOAD_DIR, rel_path)
    try:
        os.remove(p)
    except OSError:
        pass


def delete_essay_dir(essay_id):
    """Remove an essay's upload folder once it's empty (called after deleting plates)."""
    d = os.path.join(UPLOAD_DIR, f"essay_{essay_id}")
    try:
        os.rmdir(d)
    except OSError:
        pass
