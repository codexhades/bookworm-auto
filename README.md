# Bookworm Adventures Auto-Player (research)

A small, self-contained Python experiment that plays the best word automatically in
**Bookworm Adventures Deluxe** (PopCap, 2006) — built to explore bitmap-font OCR,
compressed word-list decoding, PopCap PAK unpacking and message-based input injection.

It ships **no game assets**. The dictionary and font glyphs are generated locally from
your own copy of the game (see Setup).

---

## What it does

* Captures the game window (no focus required, no cursor movement).
* Recognizes the 16 board letters by template matching against the game's own bitmap font.
* Finds the highest-scoring word using DFS over 8-neighbour adjacency with prefix pruning,
  from the game's own word list.
* Clicks the tiles in order, verifies each one lifts, presses **Attack**, then waits for
  the next turn and repeats.
* **INSERT** toggles the cheat on/off. **F9** quits.
* It never touches dialogs, menus or cutscenes — you keep playing those yourself.

## Why this exists (research / learning)

* Decoding the PopCap PAK container (XOR 0xF7, `0xBAC04AC0` magic) to get assets for analysis.
* Decoding the game's compressed prefix word list (`data/compressed.txt`).
* OCR of a bitmap font atlas (`CooperBlack20.gif/.txt`) with normalised IoU matching.
* Trie/prefix-pruned word search on a 4×4 board.
* Win32 `PostMessage` input injection that avoids hijacking the real mouse/focus.
* Small UI state machine (board present/stable, word tray, pause ribbon, popups).

## Requirements

* Windows 10/11
* Python 3.10+ with Pillow (`pip install pillow`)
* Your own copy of **Bookworm Adventures Deluxe v1.0.1.100** (windowed mode, 800×600)

## Setup (all game data is generated from your own installation)

```bat
:: 1. unpack the game's resources
python pak_unpack.py "C:\Program Files (x86)\PopCap Games\Bookworm Adventures Deluxe\main.pak" pak_unpacked

:: 2. decode the word list used by the game
python decode_wordlist.py pak_unpacked/data/compressed.txt dictionary.txt

:: 3. extract the Cooper Black glyph templates for OCR
python ocr_dev.py pak_unpacked/fonts .

:: 4. run the cheat
python bwa_cheat.py
```

When the console says `INSERT = toggle on/off`, press **INSERT** while the game is
running and on a battle board.

> The game auto-pauses when its window loses focus. The tool detects the pause ribbon
> and idles; press **Space** in the game to resume (Space is the game's pause key, so the
> tool never sends it unless it has just detected the paused state).

## Building a standalone exe

```bat
pyinstaller --onefile --console --name BookwormAuto ^
  --add-data "dictionary.txt;." --add-data "CooperBlack20;CooperBlack20" bwa_cheat.py
```

The exe contains only your code and the data generated from your copy of the game.

## How it works (short version)

| Step | File | Notes |
|------|------|-------|
| Capture | `capture.py` | `BitBlt`/`PrintWindow` from the game window into a PIL image |
| OCR | `reader.py` | 36×34 crop per tile → binarise → normalise → IoU vs. A–Z glyph masks |
| Solver | `solver.py` | DFS + prefix set over 167k words; 8-neighbour, no tile reuse |
| Input | `bwa_cheat.py` | `PostMessage(WM_LBUTTONDOWN/UP)` with client coordinates |
| States | `bwa_cheat.py` | board-full/stable checks, tray-card detection, pause ribbon, popup detection |

Validation trick: the game lights the **Attack** button green only when the current
letters form a valid word, so when a lower-confidence OCR guess is wrong the tool sees a
grey button, clears the tray with a click on the last letter card, and tries the next word.

## Legal / ethical notes

* This is for a single-player, offline game; it does not affect other players, online
  services or anti-cheat systems.
* PopCap, Bookworm and related marks and assets belong to PopCap/EA. **This repository
  contains no game data**: `dictionary.txt`, `pak_unpacked/` and `CooperBlack20/` are
  generated locally from your own installation and must not be redistributed.
* For research and learning only.

## License

MIT — see [LICENSE](LICENSE). Applies to the code only, not to game data.
