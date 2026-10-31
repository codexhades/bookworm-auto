"""Board reader: capture game window, recognize the 4x4 tiles via font templates."""
import ctypes
import os
import sys
import tempfile
import time

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = HERE
sys.path.insert(0, HERE)

from capture import find_game_hwnd, capture, get_window  # noqa: E402

TILE_X = [325, 375, 425, 475]
TILE_Y = [331, 382, 433, 484]
CELL_W, CELL_H = 36, 34
CANVAS_W, CANVAS_H = 56, 28
# when frozen into the exe, PyInstaller unpacks data files next to sys._MEIPASS
_RES = getattr(sys, "_MEIPASS", None)
GLYPH_DIR = os.environ.get("BWA_FONT_DIR") or (
    os.path.join(_RES, "CooperBlack20") if _RES else os.path.join(HERE, "CooperBlack20")
)

user32 = ctypes.windll.user32


def client_origin(hwnd):
    pt = ctypes.wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y


def grab():
    hwnd = find_game_hwnd()
    if not hwnd:
        raise RuntimeError("game window not found")
    tmp = os.path.join(tempfile.gettempdir(), "bwa_grab.png")
    capture(hwnd, tmp, quiet=True)
    img = Image.open(tmp).convert("RGB")
    os.remove(tmp)
    return img


def dark_mask(img, threshold=90):
    g = img.convert("L")
    return g.point(lambda v: 255 if v < threshold else 0)


def bright_mask(img, threshold=128):
    g = img.convert("L")
    return g.point(lambda v: 255 if v > threshold else 0)


def normalize(mask):
    bbox = mask.getbbox()
    if not bbox:
        return None
    crop = mask.crop(bbox)
    w, h = crop.size
    if h < 8 or w < 3:
        return None
    scale = min(24 / h, (CANVAS_W - 8) / w, 2.5)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    crop = crop.resize((nw, nh), Image.NEAREST)
    out = Image.new("1", (CANVAS_W, CANVAS_H), 0)
    out.paste(crop, ((CANVAS_W - nw) // 2, (CANVAS_H - nh) // 2))
    return out


def iou(a, b):
    ap, bp = a.load(), b.load()
    inter = union = 0
    for y in range(CANVAS_H):
        for x in range(CANVAS_W):
            av, bv = ap[x, y], bp[x, y]
            if av or bv:
                union += 1
                if av and bv:
                    inter += 1
    return inter / union if union else 0.0


def load_templates(font_dir=GLYPH_DIR):
    templates = {}
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        p = os.path.join(font_dir, letter + ".png")
        if not os.path.exists(p):
            continue
        m = bright_mask(Image.open(p))
        n = normalize(m)
        if n is not None:
            templates[letter] = n
    return templates


TEMPLATES = None


def read_board(img):
    """img: window capture including borders. Returns list of 16 (letter, score, margin, brightness)."""
    global TEMPLATES
    if TEMPLATES is None:
        TEMPLATES = load_templates()
    out = []
    for r in range(4):
        for c in range(4):
            cx = TILE_X[c] + 3  # image coords = client + (3, 26)
            cy = TILE_Y[r] + 26
            crop = img.crop((cx - CELL_W // 2, cy - CELL_H // 2, cx + CELL_W // 2, cy + CELL_H // 2))
            g = crop.convert("L")
            hist = g.histogram()
            mean = sum(i * n for i, n in enumerate(hist)) / (crop.width * crop.height)
            m = dark_mask(crop)
            n = normalize(m)
            if n is None:
                out.append(("?", 0.0, 0.0, mean))
                continue
            scores = sorted(((iou(n, t), letter) for letter, t in TEMPLATES.items()), reverse=True)
            top, second = scores[0], scores[1]
            out.append((top[1], top[0], top[0] - second[0], mean))
    return out


def grid_string(cells):
    return "".join(c[0] for c in cells)


if __name__ == "__main__":
    img = grab()
    cells = read_board(img)
    for r in range(4):
        row = cells[r * 4 : r * 4 + 4]
        print(" ".join(f"{c[0]}({c[1]:.2f})" for c in row))
    print("grid:", grid_string(cells))
    print("min score:", min(c[1] for c in cells), "min margin:", min(c[2] for c in cells))
