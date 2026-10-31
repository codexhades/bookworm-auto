"""Capture the Bookworm Adventures window to a PNG.

Pure ctypes + Pillow. Usage:
  python capture.py --list
  python capture.py --out shot.png            # auto-find game window
  python capture.py --hwnd 0x1234 --out shot.png
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import os
import sys

from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()

TITLE_HINTS = ("bookworm", "popcap")


def enum_windows():
    wins = []
    proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, lparam):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 2)
        user32.GetWindowTextW(hwnd, buf, length + 2)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        r = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        wins.append(
            dict(
                hwnd=int(hwnd),
                pid=pid.value,
                title=buf.value,
                cls=cls.value,
                rect=(r.left, r.top, r.right, r.bottom),
                visible=bool(user32.IsWindowVisible(hwnd)),
            )
        )
        return True

    user32.EnumWindows(proc(cb), 0)
    return wins


def find_game_hwnd():
    for w in enum_windows():
        t = w["title"].lower()
        if any(h in t for h in TITLE_HINTS):
            return w["hwnd"]
    # Any window owned by a BookwormAdventures.exe process
    try:
        import subprocess

        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq BookwormAdventures.exe", "/FO", "CSV", "/NH"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        pids = {int(line.split('","')[1]) for line in out.splitlines() if line.startswith('"Bookworm')}
        for w in enum_windows():
            if w["pid"] in pids and w["visible"] and (w["rect"][2] - w["rect"][0]) > 200:
                return w["hwnd"]
    except Exception:
        pass
    return None


def get_window(hwnd):
    for w in enum_windows():
        if w["hwnd"] == hwnd:
            return w
    raise SystemExit(f"window {hwnd} not found")


def capture(hwnd, out_path, quiet=False):
    w = get_window(hwnd)
    left, top, right, bottom = w["rect"]
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        raise SystemExit(f"bad window rect {w['rect']}")

    hdc_screen = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    bmp = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
    gdi32.SelectObject(hdc_mem, bmp)

    # Try full-content render first, then plain BitBlt from the window DC.
    ok = user32.PrintWindow(hwnd, hdc_mem, 2)
    if not ok:
        gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, 0, 0, 0x00CC0020)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wt.DWORD),
            ("biWidth", wt.LONG),
            ("biHeight", wt.LONG),
            ("biPlanes", wt.WORD),
            ("biBitCount", wt.WORD),
            ("biCompression", wt.DWORD),
            ("biSizeImage", wt.DWORD),
            ("biXPelsPerMeter", wt.LONG),
            ("biYPelsPerMeter", wt.LONG),
            ("biClrUsed", wt.DWORD),
            ("biClrImportant", wt.DWORD),
        ]

    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth = width
    bi.biHeight = -height  # top-down
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = 0

    buf = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(hdc_mem, bmp, 0, height, buf, ctypes.byref(bi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_screen)

    img = Image.frombuffer("RGB", (width, height), buf, "raw", "BGRX", 0, 1)
    img.save(out_path)
    if not quiet:
        print(f"saved {out_path} size={img.size} hwnd={hwnd} title={w['title']!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--hwnd", type=lambda s: int(s, 0), default=None)
    ap.add_argument("--out", default="shot.png")
    args = ap.parse_args()

    if args.list:
        for w in enum_windows():
            if w["visible"] and (w["rect"][2] - w["rect"][0]) > 100:
                print(
                    f"hwnd={w['hwnd']:#010x} pid={w['pid']:6d} rect={w['rect']} "
                    f"class={w['cls']!r} title={w['title']!r}"
                )
        return

    hwnd = args.hwnd or find_game_hwnd()
    if not hwnd:
        raise SystemExit("game window not found")
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    capture(hwnd, out)


if __name__ == "__main__":
    main()
