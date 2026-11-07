from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path

from before_after.composite import create_before_after_jpeg_bytes
from before_after.pairing import Pair, match_before_after_folder, match_before_after_uploads


def _safe_stem(name: str) -> str:
    stem = Path(name).stem
    safe = re.sub(r"[^\w\-]+", "_", stem).strip("_")
    return safe or "photo"


def output_name_for_pair(pair: Pair, index: int) -> str:
    a = _safe_stem(pair.before_name)
    b = _safe_stem(pair.after_name)
    if a == b:
        return f"{a}_before_after.jpg"
    return f"pair_{index:03d}_{a}__{b}_before_after.jpg"


def process_folder(
    input_dir: Path,
    output_dir: Path,
    *,
    canvas_size: int = 2048,
    jpeg_quality: int = 92,
    min_score: float = 0.38,
) -> tuple[list[Path], list[str]]:
    pairs, unmatched = match_before_after_folder(input_dir, min_score=min_score)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for index, pair in enumerate(pairs, start=1):
        out_name = output_name_for_pair(pair, index)
        out_path = output_dir / out_name
        create_before_after_jpeg_bytes(
            pair.before_image,
            pair.after_image,
            out_path,
            canvas_size=canvas_size,
            jpeg_quality=jpeg_quality,
        )
        written.append(out_path)
    return written, unmatched


def process_uploads_to_zip(
    files: list[tuple[str, bytes]],
    *,
    canvas_size: int = 2048,
    jpeg_quality: int = 92,
    min_score: float = 0.38,
) -> tuple[bytes | None, list[str], int]:
    pairs, unmatched = match_before_after_uploads(files, min_score=min_score)
    if not pairs:
        return None, unmatched, 0

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for index, pair in enumerate(pairs, start=1):
            name = output_name_for_pair(pair, index)
            jpg = create_before_after_jpeg_bytes(
                pair.before_image,
                pair.after_image,
                None,
                canvas_size=canvas_size,
                jpeg_quality=jpeg_quality,
            )
            zf.writestr(name, jpg)

    return buffer.getvalue(), unmatched, len(pairs)
