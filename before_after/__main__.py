from __future__ import annotations

import argparse
import sys
from pathlib import Path

from before_after.two_photo import composite_two


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Combine two photos into one before/after JPG.",
    )
    parser.add_argument("photo_one", type=Path, help="First photo (or before if --no-auto).")
    parser.add_argument("photo_two", type=Path, help="Second photo (or after if --no-auto).")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("before_after.jpg"),
        help="Output JPG path (default: before_after.jpg).",
    )
    parser.add_argument(
        "--no-auto",
        action="store_true",
        help="Photo 1 = BEFORE, photo 2 = AFTER (skip auto-detect).",
    )
    parser.add_argument("--size", type=int, default=2048, help="Canvas size (default: 2048).")
    parser.add_argument("--quality", type=int, default=92, help="JPEG quality (default: 92).")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    one = args.photo_one.expanduser().resolve()
    two = args.photo_two.expanduser().resolve()
    if not one.is_file() or not two.is_file():
        print("Both photo paths must exist.", file=sys.stderr)
        return 1

    out = args.output.expanduser().resolve()
    jpg = composite_two(
        one.read_bytes(),
        two.read_bytes(),
        auto_detect=not args.no_auto,
        canvas_size=args.size,
        jpeg_quality=args.quality,
    )
    out.write_bytes(jpg)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
