"""Extract the game's Cooper Black glyph images (A-Z) for OCR templates.

Usage:
    python ocr_dev.py [fonts_dir] [out_dir]

fonts_dir should contain CooperBlack20.gif and CooperBlack20.txt (extracted
from main.pak).  Writes out_dir/CooperBlack20/A.png ... Z.png.
"""
import os
import sys

from PIL import Image


def parse_font(txt_path):
    """Return (chars, rects) for the font atlas.  Rects are (x, y, w, h)."""
    txt = open(txt_path, "rb").read().decode("latin-1")
    rstart = txt.index("Define RectList")
    rstart = txt.index("(", rstart)
    rend = txt.index(");", rstart)
    nums = [
        int(n)
        for n in txt[rstart + 1 : rend].replace("(", " ").replace(")", " ").replace(",", " ").split()
    ]
    rects = [(nums[i], nums[i + 1], nums[i + 2], nums[i + 3]) for i in range(0, len(nums), 4)]
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ", rects


def extract(fonts_dir, out_dir, font="CooperBlack20"):
    chars, rects = parse_font(os.path.join(fonts_dir, font + ".txt"))
    atlas = Image.open(os.path.join(fonts_dir, font + ".gif")).convert("RGBA")
    target = os.path.join(out_dir, font)
    os.makedirs(target, exist_ok=True)
    for ch, (x, y, w, h) in zip(chars, rects):
        atlas.crop((x, y, x + w, y + h)).save(os.path.join(target, ch + ".png"))
    print(f"wrote {len(chars)} glyphs to {target}")


def main():
    fonts_dir = sys.argv[1] if len(sys.argv) > 1 else "pak_unpacked/fonts"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    extract(fonts_dir, out_dir)


if __name__ == "__main__":
    main()
