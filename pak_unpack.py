"""Unpack the game's main.pak (PopCap PAK container, XOR-obfuscated with 0xF7).

Usage:
    python pak_unpack.py <main.pak> [output_dir]

The PAK format (also used by other PopCap titles):
  whole file XOR 0xF7
  header    : u32 magic 0xBAC04AC0, u32 version (0)
  catalog   : u8 type(0), u8 name_len, name, u32 size, u64 FILETIME ...
              ends with a non-zero type byte
  contents  : raw file data concatenated in catalog order
"""
import os
import sys


def unpack(src, out):
    data = bytearray(b ^ 0xF7 for b in open(src, "rb").read())

    magic = int.from_bytes(data[0:4], "little")
    version = int.from_bytes(data[4:8], "little")
    if magic != 0xBAC04AC0:
        raise SystemExit(f"not a PopCap PAK (magic {magic:#x})")
    if version != 0:
        raise SystemExit(f"unsupported PAK version {version}")

    pos = 8
    records = []
    while True:
        rtype = data[pos]
        if rtype != 0:
            pos += 1
            break
        namelen = data[pos + 1]
        name = data[pos + 2 : pos + 2 + namelen].decode("latin-1")
        size = int.from_bytes(data[pos + 2 + namelen : pos + 6 + namelen], "little")
        records.append((name, size))
        pos += 2 + namelen + 12

    print(f"{len(records)} files, content starts at {pos:#x}")

    content = pos
    os.makedirs(out, exist_ok=True)
    for name, size in records:
        path = os.path.join(out, name.replace("\\", "/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(bytes(data[content : content + size]))
        content += size
    print(f"extracted to {out}")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "main.pak"
    out = sys.argv[2] if len(sys.argv) > 2 else "pak_unpacked"
    unpack(src, out)


if __name__ == "__main__":
    main()
