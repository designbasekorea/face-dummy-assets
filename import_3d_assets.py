#!/usr/bin/env python3
"""Import portrait source images into a Face Dummy image style.

The plugin expects two variants for every asset:

* img/<filename>.png       - 100x133 free preview
* img/pro/<filename>.png   - 600x800 paid image

This script assigns stable sequential names, keeps the original alpha channel,
updates imageMetadata2.csv, regenerates imageList.json, and records source
hashes so rerunning the import is safe.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - environment-specific
    raise SystemExit(
        "Pillow is required. Run `python3 -m pip install Pillow` once and retry."
    ) from exc


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
BASE_URL = "https://cdn.jsdelivr.net/gh/deccomm/ffdm/img"
METADATA_FIELDS = ["filename", "category", "type", "gender", "Paid", "addedAt"]
MANIFEST_FILENAME = "asset-import-manifest.json"
REVIEW_FILENAME = "asset-import-review.csv"


def natural_key(value: str) -> list[Any]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", value)]


def source_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def guess_gender(filename: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", filename.casefold())
    words = set(text.split())

    if {"non", "binary"}.issubset(words) or "nonbinary" in words:
        return "Non-binary"
    if words & {"female", "woman", "women", "girl", "lady"}:
        return "Female"
    if words & {"male", "man", "men", "boy", "gentleman"}:
        return "Male"
    return ""


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return [
            {field: row.get(field, "") for field in METADATA_FIELDS}
            for row in csv.DictReader(source)
        ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=METADATA_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write("\n")


def asset_number(filename: str, prefix: str) -> int | None:
    match = re.fullmatch(rf"{re.escape(prefix)}-(\d+)\.png", filename)
    return int(match.group(1)) if match else None


def next_asset_number(metadata_rows: list[dict[str, str]], base_dir: Path, prefix: str) -> int:
    numbers = [
        number
        for row in metadata_rows
        if (number := asset_number(row.get("filename", ""), prefix)) is not None
    ]
    for path in base_dir.glob(f"{prefix}-*.png"):
        if (number := asset_number(path.name, prefix)) is not None:
            numbers.append(number)
    return max(numbers, default=0) + 1


def fit_to_canvas(image: Image.Image, width: int, height: int) -> Image.Image:
    """Fit the complete image into a transparent canvas without cropping."""
    source_width, source_height = image.size
    scale = min(width / source_width, height / source_height)
    resized_width = max(1, round(source_width * scale))
    resized_height = max(1, round(source_height * scale))
    resized = image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    left = (width - resized_width) // 2
    top = (height - resized_height) // 2
    canvas.alpha_composite(resized, (left, top))
    return canvas


def save_variant(source: Path, destination: Path, width: int, height: int) -> None:
    with Image.open(source) as opened:
        image = fit_to_canvas(opened.convert("RGBA"), width, height)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, format="PNG", optimize=True, compress_level=9)


def regenerate_image_list(base_dir: Path) -> None:
    image_urls = [
        f"{BASE_URL}/{path.name}"
        for path in sorted(base_dir.glob("*.png"), key=lambda item: natural_key(item.name))
    ]
    write_json(base_dir / "imageList.json", image_urls)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a new Face Dummy image style.")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("incoming/3d"),
        help="Folder containing source images (default: incoming/3d)",
    )
    parser.add_argument(
        "--type",
        default="3D Avatar",
        help="Metadata type label shown in the plugin (default: 3D Avatar)",
    )
    parser.add_argument(
        "--category",
        default="Graphic",
        help="Metadata category label shown in the plugin (default: Graphic)",
    )
    parser.add_argument(
        "--prefix",
        default="graphic-3d-avatar",
        help="Filename prefix for the new style (default: graphic-3d-avatar)",
    )
    parser.add_argument(
        "--preview-size",
        default="100x133",
        help="Free preview dimensions as WIDTHxHEIGHT (default: 100x133)",
    )
    parser.add_argument(
        "--paid-size",
        default="600x800",
        help="Paid image dimensions as WIDTHxHEIGHT (default: 600x800)",
    )
    parser.add_argument(
        "--paid",
        default="Y",
        choices=["Y", ""],
        help="Paid metadata value for imported images (default: Y)",
    )
    parser.add_argument(
        "--remove-existing-prefix",
        help="Remove assets recorded in the manifest whose filenames start with this prefix before importing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the import plan without writing images or metadata.",
    )
    return parser.parse_args()


def parse_size(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", value.lower().strip())
    if not match:
        raise ValueError(f"Invalid size '{value}'. Use WIDTHxHEIGHT, for example 600x800.")
    width, height = int(match.group(1)), int(match.group(2))
    if width < 1 or height < 1:
        raise ValueError("Image dimensions must be positive.")
    return width, height


def main() -> int:
    args = parse_args()
    repo_dir = Path(__file__).resolve().parent
    source_dir = args.source_dir.expanduser().resolve()
    base_dir = repo_dir / "img"
    pro_dir = base_dir / "pro"
    metadata_path = repo_dir / "imageMetadata2.csv"
    manifest_path = repo_dir / MANIFEST_FILENAME
    review_path = repo_dir / REVIEW_FILENAME

    try:
        preview_width, preview_height = parse_size(args.preview_size)
        paid_width, paid_height = parse_size(args.paid_size)
    except ValueError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    if not source_dir.exists():
        print(f"[FAIL] Source directory does not exist: {source_dir}", file=sys.stderr)
        return 1

    source_files = sorted(
        (path for path in source_dir.iterdir() if path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS),
        key=lambda path: natural_key(path.name),
    )
    if not source_files:
        print(f"[INFO] No supported images found in: {source_dir}")
        return 0

    metadata_rows = load_csv(metadata_path)
    manifest = load_json(manifest_path, {})
    if not isinstance(manifest, dict):
        manifest = {}

    if args.remove_existing_prefix:
        legacy_filenames = [
            filename
            for filename in manifest
            if filename.startswith(args.remove_existing_prefix)
        ]
        if legacy_filenames and not args.dry_run:
            for filename in legacy_filenames:
                for directory in (base_dir, pro_dir):
                    output_path = directory / filename
                    if output_path.exists():
                        output_path.unlink()
            metadata_rows = [
                row for row in metadata_rows if row.get("filename") not in legacy_filenames
            ]
            manifest = {
                filename: entry
                for filename, entry in manifest.items()
                if filename not in legacy_filenames
            }
            print(f"[MIGRATE] Removed {len(legacy_filenames)} previously imported asset(s).")

    known_hashes = {
        entry.get("sha256")
        for entry in manifest.values()
        if isinstance(entry, dict) and entry.get("sha256")
    }
    next_number = next_asset_number(metadata_rows, base_dir, args.prefix)
    new_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    skipped = 0

    for source in source_files:
        digest = source_hash(source)
        if digest in known_hashes:
            skipped += 1
            continue

        filename = f"{args.prefix}-{next_number}.png"
        gender = guess_gender(source.stem)
        print(f"[PLAN] {source.name} -> {filename} ({gender or 'gender review'})")
        if not args.dry_run:
            save_variant(source, base_dir / filename, preview_width, preview_height)
            save_variant(source, pro_dir / filename, paid_width, paid_height)
            manifest[filename] = {
                "addedAt": datetime.now(timezone.utc).isoformat(),
                "source": source.name,
                "sha256": digest,
                "gender": gender,
                "type": args.type,
                "previewSize": f"{preview_width}x{preview_height}",
                "paidSize": f"{paid_width}x{paid_height}",
            }

            new_rows.append(
                {
                    "filename": filename,
                    "category": args.category,
                    "type": args.type,
                    "gender": gender,
                    "Paid": args.paid,
                    "addedAt": manifest[filename]["addedAt"],
                }
            )
            if not gender:
                review_rows.append({"filename": filename, "source": source.name, "gender": ""})

        next_number += 1

    if args.dry_run:
        print(f"[INFO] Dry run: {len(source_files) - skipped} new, {skipped} already imported.")
        return 0

    if not new_rows:
        print(f"[INFO] Nothing to import. {skipped} source image(s) already imported.")
        return 0

    metadata_rows.extend(new_rows)
    write_csv(metadata_path, metadata_rows)
    write_json(manifest_path, manifest)

    if review_rows:
        with review_path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=["filename", "source", "gender"], lineterminator="\n")
            writer.writeheader()
            writer.writerows(review_rows)
    elif review_path.exists():
        review_path.unlink()

    regenerate_image_list(base_dir)
    print(f"[DONE] Imported {len(new_rows)} image(s); skipped {skipped} duplicate(s).")
    print(f"[NEXT] Review: {review_path.name if review_rows else 'no ambiguous gender names'}")
    print("[NEXT] Run `npm run assets:check`, then commit and push this ffdm repository.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
