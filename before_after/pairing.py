from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from before_after.images import IMAGE_EXTENSIONS, load_rgb, load_rgb_with_meta
from before_after.matching import PhotoSignature, build_signature, match_pairs


@dataclass(frozen=True)
class Pair:
    before: Path | None
    after: Path | None
    before_name: str
    after_name: str
    before_image: Image.Image
    after_image: Image.Image
    score: float
    method: str


def iter_image_paths(folder: Path) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            paths.append(path)
    return paths


def _signatures_from_paths(paths: list[Path]) -> list[PhotoSignature]:
    signatures: list[PhotoSignature] = []
    for index, path in enumerate(paths):
        image, captured_at = load_rgb_with_meta(path)
        signatures.append(build_signature(index, path.name, image, captured_at=captured_at))
    return signatures


def _signatures_from_uploads(files: list[tuple[str, bytes]]) -> list[PhotoSignature]:
    signatures: list[PhotoSignature] = []
    for index, (name, data) in enumerate(files):
        image, captured_at = load_rgb_with_meta(data)
        signatures.append(build_signature(index, name, image, captured_at=captured_at))
    return signatures


def match_before_after_folder(
    folder: Path,
    *,
    min_score: float = 0.38,
) -> tuple[list[Pair], list[str]]:
    paths = iter_image_paths(folder)
    if not paths:
        return [], []
    return match_before_after_paths(paths, min_score=min_score)


def match_before_after_paths(
    paths: list[Path],
    *,
    min_score: float = 0.38,
) -> tuple[list[Pair], list[str]]:
    signatures = _signatures_from_paths(paths)
    return _to_pairs(signatures, min_score=min_score, method_prefix="visual")


def match_before_after_uploads(
    files: list[tuple[str, bytes]],
    *,
    min_score: float = 0.38,
) -> tuple[list[Pair], list[str]]:
    signatures = _signatures_from_uploads(files)
    return _to_pairs(signatures, min_score=min_score, method_prefix="visual")


def _to_pairs(
    signatures: list[PhotoSignature],
    *,
    min_score: float,
    method_prefix: str,
) -> tuple[list[Pair], list[str]]:
    raw_pairs, unmatched = match_pairs(signatures, min_score=min_score)
    pairs: list[Pair] = []
    for before, after, score in raw_pairs:
        before_path = None
        after_path = None
        pairs.append(
            Pair(
                before=before_path,
                after=after_path,
                before_name=before.name,
                after_name=after.name,
                before_image=before.image,
                after_image=after.image,
                score=score,
                method=f"{method_prefix}:score={score:.2f}",
            )
        )

    # Re-attach paths when signatures came from disk (stored only in name for uploads).
    unmatched_names = [sig.name for sig in unmatched]
    return pairs, unmatched_names


def match_before_after(folder: Path, similarity_threshold: int = 14) -> tuple[list[Pair], list[Path]]:
    """CLI compatibility wrapper."""
    pairs, unmatched_names = match_before_after_folder(
        folder,
        min_score=max(0.45, 0.52 - (similarity_threshold - 14) * 0.01),
    )
    unmatched_paths = [folder / name for name in unmatched_names]
    # Fix paths on pairs
    fixed: list[Pair] = []
    for pair in pairs:
        fixed.append(
            Pair(
                before=folder / pair.before_name,
                after=folder / pair.after_name,
                before_name=pair.before_name,
                after_name=pair.after_name,
                before_image=pair.before_image,
                after_image=pair.after_image,
                score=pair.score,
                method=pair.method,
            )
        )
    return fixed, unmatched_paths
