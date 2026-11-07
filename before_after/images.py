from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}

_EXIF_TIME_TAGS = (36867, 36868, 306)  # DateTimeOriginal, DateTimeDigitized, DateTime


def is_image_filename(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_EXTENSIONS


def capture_time_from_image(img: Image.Image) -> datetime | None:
    exif = img.getexif()
    if exif:
        for tag in _EXIF_TIME_TAGS:
            raw = exif.get(tag)
            if not raw:
                continue
            try:
                return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue
    return None


def load_rgb(source: Path | bytes) -> Image.Image:
    image, _ = load_rgb_with_meta(source)
    return image


def load_rgb_with_meta(source: Path | bytes) -> tuple[Image.Image, datetime | None]:
    if isinstance(source, bytes):
        with Image.open(BytesIO(source)) as img:
            oriented = ImageOps.exif_transpose(img)
            captured = capture_time_from_image(oriented)
            return oriented.convert("RGB"), captured
    with Image.open(source) as img:
        oriented = ImageOps.exif_transpose(img)
        captured = capture_time_from_image(oriented)
        return oriented.convert("RGB"), captured


def sharpness_score(img: Image.Image) -> float:
    gray = np.asarray(img.convert("L"), dtype=np.float32)
    if gray.size < 4:
        return 0.0
    dx = np.diff(gray, axis=1)
    dy = np.diff(gray, axis=0)
    return float(np.var(dx) + np.var(dy))


def contrast_score(img: Image.Image) -> float:
    gray = np.asarray(img.convert("L"), dtype=np.float32)
    return float(gray.std())


def gray_thumbnail(img: Image.Image, size: int = 256) -> np.ndarray:
    thumb = img.convert("L").resize((size, size), Image.Resampling.BILINEAR)
    arr = np.asarray(thumb, dtype=np.float32)
    arr -= arr.mean()
    norm = np.linalg.norm(arr)
    if norm > 1e-6:
        arr /= norm
    return arr.reshape(-1)


def aspect_ratio(img: Image.Image) -> float:
    w, h = img.size
    return w / h if h else 1.0
