from __future__ import annotations

from before_after.composite import create_before_after_jpeg_bytes
from before_after.images import load_rgb, sharpness_score, contrast_score
from PIL import Image


def pick_before_after(a: Image.Image, b: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Dirtier / softer image goes on the BEFORE (left) side."""
    score_a = (sharpness_score(a), contrast_score(a))
    score_b = (sharpness_score(b), contrast_score(b))
    if score_a <= score_b:
        return a, b
    return b, a


def composite_two(
    first: bytes,
    second: bytes,
    *,
    auto_detect: bool = True,
    canvas_size: int = 2048,
    jpeg_quality: int = 92,
) -> bytes:
    img_a = load_rgb(first)
    img_b = load_rgb(second)
    if auto_detect:
        before, after = pick_before_after(img_a, img_b)
    else:
        before, after = img_a, img_b
    return create_before_after_jpeg_bytes(
        before,
        after,
        None,
        canvas_size=canvas_size,
        jpeg_quality=jpeg_quality,
    )
