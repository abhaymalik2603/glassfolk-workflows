from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from before_after.images import load_rgb


def _cover_resize(img: Image.Image, width: int, height: int) -> Image.Image:
    if width <= 0 or height <= 0:
        raise ValueError("Target dimensions must be positive")

    src_w, src_h = img.size
    scale = max(width / src_w, height / src_h)
    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf"),
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _draw_centered_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_x: int,
    top_y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = center_x - text_w // 2
    y = top_y
    stroke = max(2, int(font.size * 0.08)) if hasattr(font, "size") else 2
    draw.text((x, y), text, font=font, fill=(255, 255, 255), stroke_width=stroke, stroke_fill=(0, 0, 0))


def _render_before_after_canvas(
    before: Image.Image,
    after: Image.Image,
    *,
    canvas_size: int = 2048,
    border: int = 24,
    gutter: int = 12,
) -> Image.Image:
    canvas_size = max(512, canvas_size)
    border = max(8, border)
    gutter = max(4, gutter)

    inner = canvas_size - 2 * border
    panel_w = (inner - gutter) // 2
    panel_h = inner
    label_band = max(72, int(canvas_size * 0.07))
    image_h = panel_h - label_band

    left_panel = _cover_resize(before, panel_w, image_h)
    right_panel = _cover_resize(after, panel_w, image_h)

    canvas = Image.new("RGB", (canvas_size, canvas_size), (255, 255, 255))
    left_x = border
    right_x = border + panel_w + gutter
    image_y = border + label_band

    canvas.paste(left_panel, (left_x, image_y))
    canvas.paste(right_panel, (right_x, image_y))

    draw = ImageDraw.Draw(canvas)
    font_size = max(28, int(canvas_size * 0.045))
    font = _load_font(font_size)
    label_y = border + int(label_band * 0.18)
    _draw_centered_label(draw, "BEFORE", left_x + panel_w // 2, label_y, font)
    _draw_centered_label(draw, "AFTER", right_x + panel_w // 2, label_y, font)
    return canvas


def create_before_after_jpeg_bytes(
    before: Image.Image | Path,
    after: Image.Image | Path,
    output_path: Path | None,
    *,
    canvas_size: int = 2048,
    border: int = 24,
    gutter: int = 12,
    jpeg_quality: int = 92,
) -> bytes:
    if isinstance(before, Path):
        before = load_rgb(before)
    if isinstance(after, Path):
        after = load_rgb(after)

    canvas = _render_before_after_canvas(
        before,
        after,
        canvas_size=canvas_size,
        border=border,
        gutter=gutter,
    )

    buffer = BytesIO()
    canvas.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True, subsampling=0)
    data = buffer.getvalue()

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.suffix.lower() not in {".jpg", ".jpeg"}:
            output_path = output_path.with_suffix(".jpg")
        output_path.write_bytes(data)

    return data


def create_before_after_jpeg(
    before_path: Path,
    after_path: Path,
    output_path: Path,
    *,
    canvas_size: int = 2048,
    border: int = 24,
    gutter: int = 12,
    jpeg_quality: int = 92,
) -> Path:
    create_before_after_jpeg_bytes(
        load_rgb(before_path),
        load_rgb(after_path),
        output_path,
        canvas_size=canvas_size,
        border=border,
        gutter=gutter,
        jpeg_quality=jpeg_quality,
    )
    if output_path.suffix.lower() not in {".jpg", ".jpeg"}:
        output_path = output_path.with_suffix(".jpg")
    return output_path
