"""Decode the game's compressed word list (data/compressed.txt).

Usage:
    python decode_wordlist.py [pak_unpacked/data/compressed.txt] [dictionary.txt]

Format: one entry per line (CRLF):
   [digits][suffix]
digits = how many characters to keep from the front of the previous word
(omitted -> same as previous), then the suffix is appended.
E.g. aah | 3ed | ing | s  ->  aah, aahed, aahing, aahs
"""
import re
import sys


def decode(src, out):
    text = open(src, "rb").read().decode("latin-1")
    lines = text.split("\r\n")
    words = []
    cur = ""
    prefix = 0
    for line in lines:
        if line == "":
            continue
        m = re.match(r"^(\d+)(.*)$", line)
        if m:
            prefix = int(m.group(1))
            suffix = m.group(2)
        else:
            suffix = line
        cur = cur[:prefix] + suffix
        words.append(cur)

    print(f"decoded {len(words)} words")
    print(f"first: {words[:10]}")
    print(f"last:  {words[-5:]}")
    print(f"sorted: {all(a <= b for a, b in zip(words, words[1:]))}")
    print(f"unique: {len(set(words)) == len(words)}")
    chars = set("".join(words))
    print(f"charset ok: {chars <= set('abcdefghijklmnopqrstuvwxyz')}")

    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(words))
    print(f"wrote {out}")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "pak_unpacked/data/compressed.txt"
    out = sys.argv[2] if len(sys.argv) > 2 else "dictionary.txt"
    decode(src, out)


if __name__ == "__main__":
    main()
