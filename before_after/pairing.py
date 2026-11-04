from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image, ImageOps

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}

BEFORE_TOKENS = frozenset(
    {
        "before",
        "b4",
        "pre",
        "dirty",
        "prior",
        "old",
    }
)
AFTER_TOKENS = frozenset(
    {
        "after",
        "aftr",
        "post",
        "clean",
        "new",
    }
)


@dataclass(frozen=True)
class Photo:
    path: Path
    phash: imagehash.ImageHash
    sharpness: float
    role: str | None  # "before" | "after" | None
    base_key: str


@dataclass(frozen=True)
class Pair:
    before: Path
    after: Path
    method: str


def iter_image_paths(folder: Path) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            paths.append(path)
    return paths


def _load_rgb(path: Path) -> Image.Image:
    with Image.open(path) as img:
        return ImageOps.exif_transpose(img.convert("RGB"))


def _sharpness_score(img: Image.Image) -> float:
    gray = np.asarray(img.convert("L"), dtype=np.float32)
    if gray.size < 4:
        return 0.0
    dx = np.diff(gray, axis=1)
    dy = np.diff(gray, axis=0)
    return float(np.var(dx) + np.var(dy))


def _tokenize_stem(stem: str) -> tuple[str | None, str]:
    lower = stem.lower()
    role: str | None = None
    cleaned = lower

    for token in BEFORE_TOKENS:
        patterns = [
            rf"\b{re.escape(token)}\b",
            rf"_{re.escape(token)}$",
            rf"^{re.escape(token)}_",
            rf"-{re.escape(token)}$",
            rf"^{re.escape(token)}-",
        ]
        for pattern in patterns:
            if re.search(pattern, cleaned):
                role = "before"
                cleaned = re.sub(pattern, "", cleaned)
                break
        if role:
            break

    if role is None:
        for token in AFTER_TOKENS:
            patterns = [
                rf"\b{re.escape(token)}\b",
                rf"_{re.escape(token)}$",
                rf"^{re.escape(token)}_",
                rf"-{re.escape(token)}$",
                rf"^{re.escape(token)}-",
            ]
            for pattern in patterns:
                if re.search(pattern, cleaned):
                    role = "after"
                    cleaned = re.sub(pattern, "", cleaned)
                    break
            if role:
                break

    cleaned = re.sub(r"[_\-\s]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\(\d+\)$", "", cleaned).strip()
    base_key = cleaned or lower
    return role, base_key


def _analyze(path: Path) -> Photo:
    img = _load_rgb(path)
    ph = imagehash.phash(img, hash_size=16)
    sharp = _sharpness_score(img)
    role, base_key = _tokenize_stem(path.stem)
    return Photo(path=path, phash=ph, sharpness=sharp, role=role, base_key=base_key)


def _assign_before_after(a: Photo, b: Photo) -> tuple[Path, Path]:
    if a.role == "before" and b.role == "after":
        return a.path, b.path
    if a.role == "after" and b.role == "before":
        return b.path, a.path
    if a.role == "before":
        return a.path, b.path
    if b.role == "before":
        return b.path, a.path
    if a.role == "after":
        return b.path, a.path
    if b.role == "after":
        return a.path, b.path
    # Dirtier / hazier glass tends to look softer (lower sharpness).
    if a.sharpness <= b.sharpness:
        return a.path, b.path
    return b.path, a.path


def _pair_by_filename(photos: list[Photo]) -> tuple[list[Pair], list[Photo]]:
    by_key: dict[str, list[Photo]] = {}
    for photo in photos:
        by_key.setdefault(photo.base_key, []).append(photo)

    pairs: list[Pair] = []
    leftover: list[Photo] = []

    for key, group in by_key.items():
        if len(group) == 2:
            before, after = _assign_before_after(group[0], group[1])
            pairs.append(Pair(before=before, after=after, method=f"filename:{key}"))
        elif len(group) > 2:
            befores = [p for p in group if p.role == "before"]
            afters = [p for p in group if p.role == "after"]
            if befores and afters:
                befores.sort(key=lambda p: p.sharpness)
                afters.sort(key=lambda p: p.sharpness, reverse=True)
                pairs.append(
                    Pair(
                        before=befores[0].path,
                        after=afters[0].path,
                        method=f"filename-group:{key}",
                    )
                )
                leftover.extend(befores[1:] + afters[1:] + [p for p in group if p.role is None])
            else:
                leftover.extend(group)
        else:
            leftover.extend(group)

    return pairs, leftover


def _pair_by_similarity(photos: list[Photo], max_distance: int = 14) -> tuple[list[Pair], list[Photo]]:
    if len(photos) < 2:
        return [], photos

    unused = set(range(len(photos)))
    pairs: list[Pair] = []

    while len(unused) >= 2:
        best: tuple[int, int, int] | None = None
        unused_list = list(unused)
        for i in range(len(unused_list)):
            for j in range(i + 1, len(unused_list)):
                ia, ib = unused_list[i], unused_list[j]
                dist = photos[ia].phash - photos[ib].phash
                if dist <= max_distance and (best is None or dist < best[2]):
                    best = (ia, ib, dist)

        if best is None:
            break

        ia, ib, dist = best
        unused.remove(ia)
        unused.remove(ib)
        before, after = _assign_before_after(photos[ia], photos[ib])
        pairs.append(Pair(before=before, after=after, method=f"similarity:d={dist}"))

    leftover = [photos[i] for i in sorted(unused)]
    return pairs, leftover


def match_before_after(folder: Path, similarity_threshold: int = 14) -> tuple[list[Pair], list[Path]]:
    paths = iter_image_paths(folder)
    if not paths:
        return [], []

    photos = [_analyze(path) for path in paths]
    filename_pairs, leftover = _pair_by_filename(photos)
    similarity_pairs, still_left = _pair_by_similarity(leftover, max_distance=similarity_threshold)

    all_pairs = filename_pairs + similarity_pairs
    unmatched = [p.path for p in still_left]
    return all_pairs, unmatched
