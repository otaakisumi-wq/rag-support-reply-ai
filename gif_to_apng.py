#!/usr/bin/env python3
"""GIF to APNG converter — output size: 600×400px, max file size: 300MB."""

import argparse
import io
import os
import sys
import tempfile
from pathlib import Path

from PIL import Image
from apng import APNG, PNG

TARGET_WIDTH = 600
TARGET_HEIGHT = 400
MAX_FILE_SIZE_BYTES = 300 * 1024 * 1024  # 300MB


def extract_gif_frames(gif_path: str) -> list[tuple[Image.Image, int]]:
    """Return list of (frame_image_RGBA, duration_ms) tuples from a GIF."""
    frames = []
    with Image.open(gif_path) as img:
        try:
            while True:
                frame = img.convert("RGBA")
                duration = img.info.get("duration", 100)  # default 100ms
                frames.append((frame.copy(), int(duration)))
                img.seek(img.tell() + 1)
        except EOFError:
            pass
    return frames


def resize_frame(frame: Image.Image, width: int, height: int) -> Image.Image:
    """Resize frame to exact dimensions using LANCZOS resampling."""
    return frame.resize((width, height), Image.LANCZOS)


def frame_to_png_bytes(frame: Image.Image) -> bytes:
    buf = io.BytesIO()
    frame.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def convert(input_path: str, output_path: str) -> None:
    print(f"Reading GIF: {input_path}")
    frames = extract_gif_frames(input_path)
    if not frames:
        print("Error: no frames found in GIF.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(frames)} frame(s). Resizing to {TARGET_WIDTH}×{TARGET_HEIGHT}...")

    apng = APNG()
    with tempfile.TemporaryDirectory() as tmpdir:
        for i, (frame_img, duration_ms) in enumerate(frames):
            resized = resize_frame(frame_img, TARGET_WIDTH, TARGET_HEIGHT)
            png_path = os.path.join(tmpdir, f"frame_{i:05d}.png")
            resized.save(png_path, format="PNG", optimize=True)

            # delay_num/delay_den express duration: num/den seconds
            # Use milliseconds as numerator, 1000 as denominator
            delay_num = max(1, duration_ms)
            apng.append_file(png_path, delay=delay_num, delay_den=1000)

    print(f"Saving APNG: {output_path}")
    apng.save(output_path)

    size_bytes = os.path.getsize(output_path)
    size_mb = size_bytes / (1024 * 1024)
    print(f"Output size: {size_mb:.2f} MB")

    if size_bytes > MAX_FILE_SIZE_BYTES:
        os.remove(output_path)
        print(
            f"Error: output ({size_mb:.2f} MB) exceeds 300 MB limit. "
            "Consider reducing the number of frames or color depth.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert GIF to APNG (600×400px, max 300MB)"
    )
    parser.add_argument("input", help="Input GIF file path")
    parser.add_argument(
        "output",
        nargs="?",
        help="Output APNG file path (default: same name with .apng extension)",
    )
    args = parser.parse_args()

    input_path = args.input
    if not os.path.isfile(input_path):
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or str(Path(input_path).with_suffix(".apng"))
    convert(input_path, output_path)


if __name__ == "__main__":
    main()
