from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import imagehash
import numpy as np
from PIL import Image

from before_after.images import aspect_ratio, contrast_score, gray_thumbnail, sharpness_score

_FILENAME_NUMBER = re.compile(r"(\d+)")


@dataclass
class PhotoSignature:
    index: int
    name: str
    image: Image.Image
    phash: imagehash.ImageHash
    sharpness: float
    contrast: float
    aspect: float
    gray_vec: np.ndarray
    orb_keypoints: int
    captured_at: datetime | None
    file_number: int | None


@dataclass(frozen=True)
class PairScore:
    total: float
    visual: float
    time: float
    temporal_adjacent: bool


def _file_number(name: str) -> int | None:
    match = _FILENAME_NUMBER.search(Path(name).stem)
    if not match:
        return None
    return int(match.group(1))


def _clahe_gray(image: Image.Image, size: int = 512) -> np.ndarray:
    gray = np.asarray(image.convert("L").resize((size, size), Image.Resampling.BILINEAR))
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _orb_match_count(gray_a: np.ndarray, gray_b: np.ndarray) -> tuple[int, int]:
    orb = cv2.ORB_create(nfeatures=2000, scaleFactor=1.2, nlevels=10)
    kp1, des1 = orb.detectAndCompute(gray_a, None)
    kp2, des2 = orb.detectAndCompute(gray_b, None)
    kp1_count = len(kp1)
    kp2_count = len(kp2)
    if des1 is None or des2 is None or len(des1) < 4 or len(des2) < 4:
        return 0, max(kp1_count, kp2_count, 1)

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    raw = bf.knnMatch(des1, des2, k=2)
    good = 0
    for pair in raw:
        if len(pair) != 2:
            continue
        m, n = pair
        if m.distance < 0.8 * n.distance:
            good += 1
    return good, max(kp1_count, kp2_count, 1)


def _hist_correlation(gray_a: np.ndarray, gray_b: np.ndarray) -> float:
    ha = cv2.calcHist([gray_a], [0], None, [32], [0, 256])
    hb = cv2.calcHist([gray_b], [0], None, [32], [0, 256])
    cv2.normalize(ha, ha, 0, 1, cv2.NORM_MINMAX)
    cv2.normalize(hb, hb, 0, 1, cv2.NORM_MINMAX)
    return float(cv2.compareHist(ha, hb, cv2.HISTCMP_CORREL))


def _phase_align_score(gray_a: np.ndarray, gray_b: np.ndarray) -> float:
    a = gray_a.astype(np.float32)
    b = gray_b.astype(np.float32)
    a -= a.mean()
    b -= b.mean()
    try:
        _, response = cv2.phaseCorrelate(a, b)
        return float(max(0.0, min(1.0, response)))
    except cv2.error:
        return 0.0


def build_signature(
    index: int,
    name: str,
    image: Image.Image,
    captured_at: datetime | None = None,
) -> PhotoSignature:
    gray_vec = gray_thumbnail(image, size=256)
    gray_cv = _clahe_gray(image, size=512)
    orb = cv2.ORB_create(nfeatures=2000)
    kp, _ = orb.detectAndCompute(gray_cv, None)
    return PhotoSignature(
        index=index,
        name=name,
        image=image,
        phash=imagehash.phash(image, hash_size=16),
        sharpness=sharpness_score(image),
        contrast=contrast_score(image),
        aspect=aspect_ratio(image),
        gray_vec=gray_vec,
        orb_keypoints=len(kp),
        captured_at=captured_at,
        file_number=_file_number(name),
    )


def _seconds_apart(a: PhotoSignature, b: PhotoSignature) -> float | None:
    if a.captured_at is None or b.captured_at is None:
        return None
    return abs((a.captured_at - b.captured_at).total_seconds())


def time_proximity_score(a: PhotoSignature, b: PhotoSignature) -> float:
    seconds = _seconds_apart(a, b)
    if seconds is None:
        return 0.0
    if seconds <= 20:
        return 1.0
    if seconds <= 90:
        return 0.85
    if seconds <= 180:
        return 0.65
    if seconds <= 600:
        return max(0.0, 0.5 - (seconds - 180) / 840)
    return 0.0


def _aspects_compatible(a: PhotoSignature, b: PhotoSignature) -> bool:
    aspect_delta = abs(a.aspect - b.aspect) / max(a.aspect, b.aspect, 1e-6)
    return aspect_delta <= 0.18


def visual_pair_score(a: PhotoSignature, b: PhotoSignature) -> float:
    if not _aspects_compatible(a, b):
        return 0.0

    corr = float(np.dot(a.gray_vec, b.gray_vec))
    corr = max(-1.0, min(1.0, corr))

    gray_a = _clahe_gray(a.image, size=512)
    gray_b = _clahe_gray(b.image, size=512)
    orb_matches, orb_scale = _orb_match_count(gray_a, gray_b)
    orb_norm = min(1.0, orb_matches / max(orb_scale * 0.10, 8.0))

    hist = max(0.0, _hist_correlation(gray_a, gray_b))
    phase = _phase_align_score(
        np.asarray(a.image.convert("L").resize((256, 256), Image.Resampling.BILINEAR)),
        np.asarray(b.image.convert("L").resize((256, 256), Image.Resampling.BILINEAR)),
    )

    ph_dist = a.phash - b.phash
    ph_norm = max(0.0, 1.0 - (ph_dist / 80.0))

    score = (
        0.30 * orb_norm
        + 0.22 * max(0.0, corr)
        + 0.18 * hist
        + 0.15 * phase
        + 0.15 * ph_norm
    )
    return float(max(0.0, min(1.0, score)))


def combined_pair_score(a: PhotoSignature, b: PhotoSignature) -> PairScore:
    visual = visual_pair_score(a, b)
    time_score = time_proximity_score(a, b)

    temporal_adjacent = False
    if a.captured_at and b.captured_at:
        temporal_adjacent = _seconds_apart(a, b) is not None and _seconds_apart(a, b) <= 120
    elif a.file_number is not None and b.file_number is not None:
        temporal_adjacent = abs(a.file_number - b.file_number) == 1

    if time_score >= 0.85:
        total = 0.45 * visual + 0.55 * time_score
    elif time_score >= 0.5:
        total = 0.60 * visual + 0.40 * time_score
    else:
        total = 0.85 * visual + 0.15 * time_score

    if temporal_adjacent and _aspects_compatible(a, b):
        total = max(total, 0.42 + 0.35 * time_score + 0.23 * visual)

    return PairScore(
        total=float(max(0.0, min(1.0, total))),
        visual=visual,
        time=time_score,
        temporal_adjacent=temporal_adjacent,
    )


def pair_quality_gate(a: PhotoSignature, b: PhotoSignature, score: PairScore) -> bool:
    sharp_ratio = max(a.sharpness, b.sharpness) / max(min(a.sharpness, b.sharpness), 1e-6)
    contrast_delta = abs(a.contrast - b.contrast)

    if score.time >= 0.65 or score.temporal_adjacent:
        if sharp_ratio >= 1.008 or contrast_delta >= 0.5 or score.visual >= 0.2:
            return True

    if sharp_ratio >= 1.02 or contrast_delta >= 1.0:
        return True

    if score.visual >= 0.45:
        return True

    return False


def assign_before_after(a: PhotoSignature, b: PhotoSignature) -> tuple[PhotoSignature, PhotoSignature]:
    if a.captured_at and b.captured_at and a.captured_at != b.captured_at:
        earlier, later = (a, b) if a.captured_at <= b.captured_at else (b, a)
        if later.sharpness >= earlier.sharpness * 0.98:
            return earlier, later

    if a.sharpness <= b.sharpness and a.contrast <= b.contrast:
        return a, b
    if b.sharpness <= a.sharpness and b.contrast <= a.contrast:
        return b, a
    if a.sharpness <= b.sharpness:
        return a, b
    return b, a


def _sort_signatures(signatures: list[PhotoSignature]) -> list[PhotoSignature]:
    def sort_key(sig: PhotoSignature) -> tuple:
        if sig.captured_at:
            return (0, sig.captured_at, sig.file_number or 0, sig.name)
        if sig.file_number is not None:
            return (1, sig.file_number, sig.name)
        return (2, sig.name)

    return sorted(signatures, key=sort_key)


def _sequential_fallback_pairs(
    signatures: list[PhotoSignature],
    used: set[int],
    *,
    min_score: float,
) -> list[tuple[PhotoSignature, PhotoSignature, float]]:
    ordered = _sort_signatures([s for s in signatures if s.index not in used])
    pairs: list[tuple[PhotoSignature, PhotoSignature, float]] = []
    i = 0
    while i + 1 < len(ordered):
        a, b = ordered[i], ordered[i + 1]
        if a.index in used or b.index in used:
            i += 1
            continue

        score = combined_pair_score(a, b)
        seconds = _seconds_apart(a, b)
        allow = False
        if score.temporal_adjacent and _aspects_compatible(a, b):
            allow = score.total >= max(0.28, min_score - 0.12)
        elif seconds is not None and seconds <= 300 and _aspects_compatible(a, b):
            allow = score.total >= max(0.32, min_score - 0.08)

        if allow and pair_quality_gate(a, b, score):
            before, after = assign_before_after(a, b)
            pairs.append((before, after, score.total))
            used.add(a.index)
            used.add(b.index)
            i += 2
            continue
        i += 1
    return pairs


def match_pairs(
    signatures: list[PhotoSignature],
    *,
    min_score: float = 0.38,
) -> tuple[list[tuple[PhotoSignature, PhotoSignature, float]], list[PhotoSignature]]:
    n = len(signatures)
    if n < 2:
        return [], signatures

    candidates: list[tuple[float, int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = signatures[i], signatures[j]
            if not _aspects_compatible(a, b):
                continue
            scored = combined_pair_score(a, b)
            if scored.total < min_score:
                continue
            if not pair_quality_gate(a, b, scored):
                continue
            candidates.append((scored.total, i, j))

    candidates.sort(key=lambda item: item[0], reverse=True)
    used: set[int] = set()
    pairs: list[tuple[PhotoSignature, PhotoSignature, float]] = []

    for score, i, j in candidates:
        if i in used or j in used:
            continue
        used.add(i)
        used.add(j)
        before, after = assign_before_after(signatures[i], signatures[j])
        pairs.append((before, after, score))

    for before, after, score in _sequential_fallback_pairs(signatures, used, min_score=min_score):
        pairs.append((before, after, score))

    unmatched = [sig for sig in signatures if sig.index not in used]
    return pairs, unmatched


# Backwards-compatible alias used in tests / docs
scene_pair_score = visual_pair_score
