from __future__ import annotations

import argparse
import sys
from pathlib import Path

from before_after.composite import create_before_after_jpeg, default_output_name
from before_after.pairing import match_before_after


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Match before/after photos and export side-by-side JPG composites.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Folder containing unsorted before and after photos.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output folder for JPG composites (default: <input>/output).",
    )
    parser.add_argument(
        "--similarity",
        type=int,
        default=14,
        help="Max perceptual hash distance when pairing by scene similarity (default: 14).",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=2048,
        help="Square canvas size in pixels (default: 2048).",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=92,
        help="JPEG quality 1-100 (default: 92).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_dir: Path = args.input.expanduser().resolve()
    if not input_dir.is_dir():
        print(f"Input folder not found: {input_dir}", file=sys.stderr)
        return 1

    output_dir = (args.output or (input_dir / "output")).expanduser().resolve()

    pairs, unmatched = match_before_after(input_dir, similarity_threshold=args.similarity)
    if not pairs:
        print("No before/after pairs found. Add photos or rename with before/after in the filename.")
        if unmatched:
            print(f"Unmatched photos ({len(unmatched)}):")
            for path in unmatched:
                print(f"  - {path.name}")
        return 1

    print(f"Found {len(pairs)} pair(s). Writing JPGs to {output_dir}")
    for pair in pairs:
        out_name = default_output_name(pair.before, pair.after)
        out_path = output_dir / out_name
        create_before_after_jpeg(
            pair.before,
            pair.after,
            out_path,
            canvas_size=args.size,
            jpeg_quality=args.quality,
        )
        print(f"  [{pair.method}] {pair.before.name} + {pair.after.name} -> {out_path.name}")

    if unmatched:
        print(f"\nUnmatched photos ({len(unmatched)}) — add labels or a matching partner:")
        for path in unmatched:
            print(f"  - {path.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
