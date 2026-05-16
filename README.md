# WSokoban

A Windows port of [xsokoban](https://github.com/andrewcmyers/xsokoban) (1989,
Andrew Myers et al.), styled after the 1993 Amiga port *ASokoban* by
Panagiotis Christias.

![WSokoban screenshot](docs/screenshot.png)

A single, portable `WSokoban.exe` (~12 MB) — no install, no DLLs to drop
alongside, no Python on the user's machine. Workbench 2.x look, two-eyed
player who tracks the direction of motion, drawstring-sack money packets
with €, all 91 levels of the original xsokoban, soft shuffling step sound,
confetti when you solve a level.

## Download

See the [Releases](../../releases) page for the latest `WSokoban.exe`. Drop
it anywhere; it runs in place. Save state and high scores write to the
folder it's in.

## Controls

- **Arrow keys** — walk / push. The eyes track your direction.
- **Buttons** — `New`, `Undo`, `Set Level`, `High Scores`, `About`,
  `Backup`/`Restore` (single in-game checkpoint), `Sound FX ON/OFF`,
  `Name`/`Load`/`Save`.
- `+` / `-` — toggle 1× through 4× window scale (window is also freely
  resizable; the viewport letter-boxes to keep the aspect ratio).
- `Q` — quit (auto-saves).

## Features

- All 91 levels from the xsokoban distribution
- Per-pack, per-level high scores with a "clean run" flag (no Undo used → `*`)
- Confetti burst on solve
- Procedurally synthesised footstep sound (no audio files bundled)
- Resizable window with pixel-perfect integer scaling
- Setting / state persists across runs (`WSokoban.data`,
  `WSokoban.scores`, `WSokoban.settings` next to the exe)

## Level packs

Beyond the bundled "Original" 91 levels, you can install any number of
extra level collections.

- **Load Level Pack** button — two ways to add packs:
  - **From file…** — open any `.sok` / `.xsb` / `.txt` Sokoban level
    file (sokobano.de, github.com, ksokoban, etc.). Multi-level files
    parsed automatically, level titles preserved.
  - **letslogic.com…** — paste your API key (one-time, from your
    [member preferences](https://www.letslogic.com)) and pick from
    670+ collections / 54,000 levels. The chosen collection downloads
    as a pack.
- **Now Playing: \<name\>** button — click to switch between any
  installed pack. Set Level, scores, and save state are scoped to the
  active pack.

Installed packs live in `packs/<pack name>/` next to the exe — copy
them between machines freely.

## Building from source

Requires Python 3.13+ and pygame-ce:

```
python -m pip install pygame-ce pyinstaller pillow
```

To build the single-file exe:

```
build.cmd
```

The build script invokes PyInstaller with the included `WSokoban.spec`. To
get the small (~12 MB) build, download
[UPX](https://upx.github.io/) and place `upx.exe` next to `build.cmd` —
`build.cmd` puts the script directory on `PATH` so PyInstaller's UPX probe
finds it. Without UPX you'll get a ~15 MB build that works just as well.

To run from source without building:

```
python main.py
```

To regenerate the icon from the original Amiga `.info` file (if you have
one):

```
python extract_icon.py path/to/ASokoban.info
```

## Credits

- **Sokoban** — Hiroyuki Imabayashi / Thinking Rabbit, 1981.
- **xsokoban** — Joseph L. Traub, Andrew Myers, and contributors. Public
  domain. The 91 level files in `screens/` come from this project verbatim.
- **ASokoban (Amiga)** — Panagiotis Christias, 1993, Aminet freeware. The
  app icon is extracted from his original `ASokoban.info` Workbench icon.
- **WSokoban** — ITViking-FIN, 2026.

## Licence

WSokoban itself is MIT-licensed (see [LICENSE](LICENSE)). For licences of
bundled libraries (pygame-ce, SDL2, FreeType, etc.) see
[NOTICES.md](NOTICES.md).
