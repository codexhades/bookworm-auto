"""Word solver for Bookworm Adventures 4x4 boards.

Adjacency: 8-neighbour (sides + diagonals), no tile reuse.
Ranking: longest word first, then highest scrabble-ish letter value, then alphabetical.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = HERE
DICT_PATH = os.environ.get("BWA_DICT") or os.path.join(HERE, "dictionary.txt")

VALUES = {
    "a": 1, "b": 3, "c": 3, "d": 2, "e": 1, "f": 4, "g": 2, "h": 4, "i": 1,
    "j": 8, "k": 5, "l": 1, "m": 3, "n": 1, "o": 1, "p": 3, "q": 10, "r": 1,
    "s": 1, "t": 1, "u": 1, "v": 4, "w": 4, "x": 8, "y": 4, "z": 10,
}


def load_dict(path=DICT_PATH):
    words = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            w = line.strip()
            if w:
                words.add(w)
    prefixes = set()
    for w in words:
        for i in range(1, len(w) + 1):
            prefixes.add(w[:i])
    return words, prefixes


def solve(letters, words, prefixes, min_len=3, max_len=16):
    """letters: 16 chars row-major. Returns list of (word, path) sorted best-first."""
    grid = [[letters[r * 4 + c].lower() for c in range(4)] for r in range(4)]
    results = []

    def dfs(r, c, path, word):
        ch = grid[r][c]
        word += ch
        if word not in prefixes:
            return
        path = path + (r * 4 + c,)
        if len(word) >= min_len and word in words:
            results.append((word, path))
        if len(word) >= max_len:
            return
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if not (dr or dc):
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < 4 and 0 <= nc < 4 and (nr * 4 + nc) not in path:
                    dfs(nr, nc, path, word)

    for r in range(4):
        for c in range(4):
            dfs(r, c, (), "")

    seen = set()
    uniq = []
    for w, p in results:
        key = (w, p)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((w, p))

    def score(item):
        w = item[0]
        return (len(w), sum(VALUES.get(ch, 0) for ch in w), w)

    uniq.sort(key=score, reverse=True)
    return uniq


def main():
    letters = sys.argv[1] if len(sys.argv) > 1 else "EUIASFUERFDNTJIS"
    words, prefixes = load_dict()
    res = solve(letters, words, prefixes)
    print(f"{len(res)} candidate words")
    for w, p in res[:25]:
        print(f"{w:14s} len={len(w)} val={sum(VALUES.get(ch,0) for ch in w):2d} path={p}")


if __name__ == "__main__":
    main()
