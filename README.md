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
  - **From file…** — open a `.sok` / `.xsb` / `.txt` Sokoban level
    file or a `.slc` (SokobanYASC XML) collection. Format is
    auto-detected; multi-level files are split into individual levels
    and titles preserved.
  - **letslogic.com…** — see the next section for one-time setup.
- **Now Playing: \<name\>** button — click to switch between any
  installed pack. Set Level, scores, and save state are scoped to the
  active pack.

Installed packs live in `packs/<pack name>/` next to the exe — copy
them between machines freely. Each pack is just a directory of
`screen.1`, `screen.2`, … files plus a small `pack.json` with metadata.

## Using letslogic.com (54,000+ levels)

[letslogic.com](https://www.letslogic.com) hosts over 54,000 Sokoban
levels across 670+ collections, free for personal use. WSokoban can
browse and download them directly, but it needs an API key tied to a
letslogic account. One-time setup, takes about a minute:

1. **Create a free account** at <https://www.letslogic.com>
   (*Register / Login* link, top of the page).
2. **Confirm your email**, then sign in.
3. **Find your API key.** With the account dropdown in the top right,
   open your **Member Preferences** page. The key is a long
   alphanumeric string near the bottom of that page — copy it to the
   clipboard.
4. **In WSokoban,** click **Load Level Pack** in the right panel and
   then **letslogic.com…** in the dialog that appears.
5. **Paste the API key** when prompted. WSokoban stores it locally so
   you only do this once.
6. The collection browser opens — scroll, pick one, click
   **Download**. It installs as a new pack and WSokoban switches to it
   immediately.

After the first time, clicking **letslogic.com…** goes straight to the
collection browser — no key prompt.

### Where the key is stored

The key lives in plain-text JSON in `WSokoban.settings` next to the
exe:

```json
{
  "sound": true,
  "current_pack": "Original",
  "letslogic_api_key": "your-key-here"
}
```

**To change or remove the key**, close WSokoban and either:
- edit `WSokoban.settings` and replace the key value, or
- delete `WSokoban.settings` entirely (sound preference and current
  pack reset to defaults; high scores in `WSokoban.scores` are
  untouched).

The next time you click **letslogic.com…**, the key prompt reappears.

### What WSokoban sends to letslogic

WSokoban uses your key only for two read-only POST requests:
- `/api/v1/collections` — to list available collections
- `/api/v1/collection/<id>` — to download a chosen collection's levels

It never submits solutions, scores, or any other data.

### Troubleshooting

- *"Could not reach letslogic.com"* — network or firewall problem.
  WSokoban talks to `https://letslogic.com/api/v1/...` over HTTPS.
- *"No collections returned"* — usually means the API key is missing
  or invalid. Re-check it on your Member Preferences page and update
  `WSokoban.settings` with the correct value.
- *"Bad JSON from server"* — letslogic returned an error page (often
  HTML) instead of JSON. Check the message for an HTTP status hint;
  503 / 502 mean the site is having a moment, try again shortly.

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
