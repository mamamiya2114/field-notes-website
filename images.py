"""Image processing for uploads — Pillow only, so it runs on any host.

Mirrors the original hand-tuned recipe: open -> fix orientation -> downscale to a
max edge -> save an optimized progressive JPEG. Everything is written into
/uploads as .jpg so the public site only ever serves web-ready images.
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

# role -> (max edge in px, JPEG quality)
SIZES = {
    "plate": (1900, 84),
    "hero": (2200, 84),
    "card": (1400, 82),
    "gallery": (1400, 82),
}
BAD_IMAGE = "That file isn't a usable image, or it's corrupted."


def _save_optimized(img, out_path, role):
    max_edge, quality = SIZES.get(role, SIZES["plate"])
    img = ImageOps.exif_transpose(img)          # honour camera rotation
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((max_edge, max_edge), Image.LANCZOS)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "JPEG", quality=quality, optimize=True, progressive=True)


def _process(file_storage, rel_dir, role, name=None):
    """Validate + optimize an uploaded FileStorage into UPLOAD_DIR/<rel_dir>.

    Returns the path relative to UPLOAD_DIR (stored in the DB, served at /uploads).
    """
    ext = os.path.splitext(file_storage.filename or "")[1].lower()
    if ext and ext not in ALLOWED_EXT:
        raise ValueError(f"Unsupported file type: {ext}")
    name = name or f"{role}_{uuid.uuid4().hex[:10]}.jpg"
    rel_path = f"{rel_dir}/{name}"
    out_path = os.path.join(UPLOAD_DIR, rel_dir, name)
    try:
        with Image.open(file_storage.stream) as img:
            img.verify()                       # detect truncated / forged files
        file_storage.stream.seek(0)
        with Image.open(file_storage.stream) as img:
            _save_optimized(img, out_path, role)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise ValueError(BAD_IMAGE)
    return rel_path


def process_upload(file_storage, essay_id, role="plate"):
    """Essay hero / plate image -> uploads/essay_<id>/."""
    return _process(file_storage, f"essay_{essay_id}", role)


def process_site_upload(file_storage, role="hero"):
    """Landing-page image (hero / about portrait) -> uploads/site/."""
    return _process(file_storage, "site", role)


def process_gallery_upload(file_storage):
    """Archive gallery photo -> uploads/gallery/."""
    return _process(file_storage, "gallery", "gallery")


def import_from_path(src_path, essay_id, role="plate", name=None):
    """Used by the seed script: optimize an existing file on disk into /uploads."""
    rel_dir = f"essay_{essay_id}"
    name = name or f"{role}_{uuid.uuid4().hex[:10]}.jpg"
    rel_path = f"{rel_dir}/{name}"
    out_path = os.path.join(UPLOAD_DIR, rel_dir, name)
    with Image.open(src_path) as img:
        _save_optimized(img, out_path, role)
    return rel_path


def delete_upload(rel_path):
    """Delete an uploaded file by its UPLOAD_DIR-relative path. No-op for anything
    that isn't under /uploads (e.g. bundled /static defaults)."""
    if not rel_path:
        return
    p = os.path.join(UPLOAD_DIR, rel_path)
    try:
        os.remove(p)
    except OSError:
        pass


def delete_essay_dir(essay_id):
    """Remove an essay's upload folder once it's empty (after deleting plates)."""
    try:
        os.rmdir(os.path.join(UPLOAD_DIR, f"essay_{essay_id}"))
    except OSError:
        pass
