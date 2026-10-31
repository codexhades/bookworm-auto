"""Bookworm Adventures Deluxe - auto best-word cheat.

Press INSERT to toggle the cheat on/off.  F9 quits.

While ON it watches the game board.  When it is your turn with a clean board it
spells the best word from the game's own dictionary, presses Attack, and waits
for the next turn.  It never moves the cursor, never takes focus, and never
clicks dialogs or menus - you keep driving the game; it just plays your words.

It works by posting window messages straight into the game window, so your
mouse and keyboard stay free.

Options (for testing from a console):  --on   start active   --turns N
"""
import ctypes
import os
import sys
import tempfile
import time

from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = HERE
sys.path.insert(0, HERE)

from capture import find_game_hwnd, capture  # noqa: E402
from reader import read_board  # noqa: E402
import solver as solverlib  # noqa: E402

user32 = ctypes.windll.user32

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001
VK_INSERT = 0x2D
VK_F9 = 0x78

TILE_X = [325, 375, 425, 475]
TILE_Y = [331, 382, 433, 484]
ATTACK = (442, 564)
BOARD_BOX = (300, 330, 510, 545)
WORD_BAND = (145, 205, 295, 625)
PAUSE_BOX = (220, 300, 580, 345)
CENTER_BOX = (250, 300, 550, 460)
TMP = os.path.join(tempfile.gettempdir(), "bwa_cheat_grab.png")


def resource(name):
    base = getattr(sys, "_MEIPASS", BASE)
    return os.path.join(base, name)


class Cheat:
    def __init__(self):
        self.active = False
        self.hwnd = None
        self.words = None
        self.prefixes = None
        self.cache = {}
        self.tried = set()
        self.board_key = ""
        self.prev_insert = False
        self.last_toggle = 0.0
        self.last_status = ""

    # ------------------------------------------------------------- resources
    def load_words(self):
        if self.words is None:
            path = os.environ.get("BWA_DICT") or resource("dictionary.txt")
            self.words, self.prefixes = solverlib.load_dict(path)

    # ------------------------------------------------------------------ input
    def post_click(self, x, y):
        lp = (int(y) << 16) | (int(x) & 0xFFFF)
        user32.PostMessageW(self.hwnd, WM_MOUSEMOVE, 0, lp)
        time.sleep(0.02)
        user32.PostMessageW(self.hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lp)
        time.sleep(0.04)
        user32.PostMessageW(self.hwnd, WM_LBUTTONUP, 0, lp)

    # ----------------------------------------------------------------- screen
    def snap(self):
        capture(self.hwnd, TMP, quiet=True)
        return Image.open(TMP).convert("RGB")

    @staticmethod
    def _mean(img, box):
        c = img.crop(box).convert("L")
        hist = c.histogram()
        return sum(i * n for i, n in enumerate(hist)) / (c.width * c.height)

    def cell_max(self, img, idx):
        r, c = divmod(idx, 4)
        cx = TILE_X[c] + 3
        cy = TILE_Y[r] + 26
        g = img.crop((cx - 13, cy - 13, cx + 13, cy + 13)).convert("L")
        hist = g.histogram()
        for v in range(255, -1, -1):
            if hist[v]:
                return v
        return 0

    def full(self, img):
        return all(self.cell_max(img, i) > 150 for i in range(16))

    def stable(self, a, b):
        return ImageChops.difference(a.crop(BOARD_BOX), b.crop(BOARD_BOX)).getbbox() is None

    def button_ready(self, img):
        px = list(img.crop((420, 575, 480, 605)).getdata())
        n = len(px)
        g = sum(p[1] for p in px) / n
        b = sum(p[2] for p in px) / n
        return g > 170 and b < 110

    def is_paused(self, img):
        return self._mean(img, PAUSE_BOX) > 130 and self._mean(img, BOARD_BOX) < 120

    def is_dialog(self, img):
        return self._mean(img, CENTER_BOX) > 150 and not self.is_paused(img)

    def bright_blobs(self, img):
        y0, y1, x0, x1 = WORD_BAND
        band = img.crop((x0, y0, x1, y1)).convert("L").point(lambda v: 255 if v > 170 else 0)
        w, h = band.size
        px = band.load()
        seen = set()
        blobs = []
        for y in range(h):
            for x in range(w):
                if px[x, y] and (x, y) not in seen:
                    stack = [(x, y)]
                    seen.add((x, y))
                    comp = []
                    while stack:
                        cx, cy = stack.pop()
                        comp.append((cx, cy))
                        for dx in (-1, 0, 1):
                            for dy in (-1, 0, 1):
                                q = (cx + dx, cy + dy)
                                if 0 <= q[0] < w and 0 <= q[1] < h and q not in seen and px[q[0], q[1]]:
                                    seen.add(q)
                                    stack.append(q)
                    if len(comp) > 250:
                        xs = [p[0] for p in comp]
                        ys = [p[1] for p in comp]
                        blobs.append((min(xs) + x0, min(ys) + y0, max(xs) + x0, max(ys) + y0))
        blobs.sort(key=lambda b: b[0])
        return blobs

    def tray_cards(self, img):
        cards = []
        for b in self.bright_blobs(img):
            w = b[2] - b[0]
            h = b[3] - b[1]
            if not (32 <= w <= 60 and 32 <= h <= 55):
                continue
            g = img.crop(b).convert("L")
            hist = g.histogram()
            if sum(hist[:90]) / (g.width * g.height) > 0.05:
                cards.append(b)
        return cards

    # ------------------------------------------------------------------ play
    def clear_tray(self):
        for _ in range(6):
            img = self.snap()
            cards = self.tray_cards(img)
            if not cards:
                return True
            b = cards[-1]
            self.post_click((b[0] + b[2]) // 2 - 3, (b[1] + b[3]) // 2 - 26)
            time.sleep(0.4)
        return False

    def spell(self, path):
        selected = 0
        for idx in path:
            if not self.check_toggle():
                return False, selected
            r, c = divmod(idx, 4)
            lifted = False
            for _ in range(2):
                self.post_click(TILE_X[c], TILE_Y[r])
                time.sleep(0.55)
                if self.cell_max(self.snap(), idx) < 100:
                    lifted = True
                    break
                time.sleep(0.2)
            if not lifted:
                return False, selected
            selected += 1
        return True, selected

    def play_turn(self, img):
        self.load_words()
        letters = "".join(c[0] for c in read_board(img))
        if "?" in letters:
            return False
        if letters != self.board_key:
            self.board_key = letters
            self.tried = set()
        if letters not in self.cache:
            self.cache[letters] = solverlib.solve(letters, self.words, self.prefixes)
        nxt = next(((w, p) for w, p in self.cache[letters] if w not in self.tried), None)
        if not nxt:
            return False
        word, path = nxt
        print(f"   board {letters} -> {word}")
        ok, selected = self.spell(path)
        if not ok:
            if selected:
                self.clear_tray()
            return False
        time.sleep(0.3)
        img = self.snap()
        if not self.button_ready(img):
            print(f"   '{word}' rejected, trying next")
            self.tried.add(word)
            self.clear_tray()
            return False
        if not self.check_toggle():
            self.clear_tray()
            return False
        self.post_click(*ATTACK)
        time.sleep(2.2)
        return True

    # ------------------------------------------------------------------ loop
    def status(self, msg):
        if msg != self.last_status:
            self.last_status = msg
            print(msg, flush=True)

    def check_toggle(self):
        """Edge-triggered INSERT toggle; returns the current on/off state."""
        ins = bool(user32.GetAsyncKeyState(VK_INSERT) & 0x8000)
        if ins and not self.prev_insert and time.time() - self.last_toggle > 0.25:
            self.active = not self.active
            self.last_toggle = time.time()
            self.last_status = ""
            print("[ON]  playing best words" if self.active else "[OFF] idle", flush=True)
        self.prev_insert = ins
        return self.active

    def find_game(self):
        h = find_game_hwnd()
        if h != self.hwnd:
            self.hwnd = h
            self.cache.clear()
            self.board_key = ""
        return h

    def run(self, start_on=False, max_turns=0):
        self.active = start_on
        print("Bookworm Adventures auto-cheat | INSERT = toggle on/off | F9 = quit", flush=True)
        print("start OFF" if not start_on else "start ON", flush=True)
        played = 0
        while True:
            if user32.GetAsyncKeyState(VK_F9) & 0x8000:
                print("quit", flush=True)
                return
            if not self.check_toggle():
                time.sleep(0.2)
                continue
            if not self.find_game():
                self.status("waiting for Bookworm Adventures window...")
                time.sleep(1.0)
                continue

            try:
                img = self.snap()
            except Exception:
                time.sleep(0.5)
                continue

            if self.is_paused(img):
                self.status("game paused - idle (press SPACE in game to resume)")
                time.sleep(0.4)
                continue
            if self.is_dialog(img):
                self.status("popup/dialog - idle (click it yourself)")
                time.sleep(0.4)
                continue
            if self.tray_cards(img):
                self.status("word in progress - idle")
                time.sleep(0.3)
                continue
            if not self.full(img):
                self.status("no board - idle")
                time.sleep(0.4)
                continue

            time.sleep(0.3)
            img2 = self.snap()
            if not self.stable(img, img2):
                time.sleep(0.3)
                continue
            self.status("your turn - playing")
            if self.play_turn(img2):
                played += 1
                if max_turns and played >= max_turns:
                    print("stopped (turn limit)", flush=True)
                    return
                time.sleep(0.5)
            else:
                time.sleep(0.8)


def main():
    args = sys.argv[1:]
    cheat = Cheat()
    cheat.run(start_on="--on" in args,
              max_turns=int(args[args.index("--turns") + 1]) if "--turns" in args else 0)


if __name__ == "__main__":
    main()
