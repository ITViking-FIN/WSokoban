# Third-party notices

WSokoban is original code (MIT, see [LICENSE](LICENSE)), but the released
binary and the `screens/` and `icon.*` files contain or derive from
third-party material. This file lists all of it.

## Game lineage

- **Sokoban** — original puzzle concept by Hiroyuki Imabayashi, published by
  Thinking Rabbit, 1981.
- **xsokoban** — X11 port by Joseph L. Traub, Andrew Myers, and contributors,
  late 1980s through 1990s. Source:
  <https://github.com/andrewcmyers/xsokoban>. Distributed in the **public
  domain**. The 91 level files in `screens/` are taken verbatim from this
  distribution.
- **ASokoban 1.1c** — Amiga implementation by Panagiotis Christias, 1993,
  distributed as freeware on Aminet. The `icon.png` / `icon.ico` files are
  derived from the original `ASokoban.info` Workbench icon (see
  `extract_icon.py` for the conversion). Used here in keeping with the
  freeware redistribution terms of the original Aminet release.

## Bundled libraries (in the released `WSokoban.exe` only)

The PyInstaller-built executable bundles the following libraries.
Source for each is available at the linked upstream.

| Library      | License            | Source                                            |
|--------------|--------------------|---------------------------------------------------|
| pygame-ce    | LGPL v2.1 or later | <https://github.com/pygame-community/pygame-ce>   |
| SDL2         | zlib               | <https://github.com/libsdl-org/SDL>               |
| SDL2_mixer   | zlib               | <https://github.com/libsdl-org/SDL_mixer>         |
| SDL2_image   | zlib               | <https://github.com/libsdl-org/SDL_image>         |
| SDL2_ttf     | zlib               | <https://github.com/libsdl-org/SDL_ttf>           |
| FreeType     | FTL or GPL v2      | <https://freetype.org>                            |
| libpng       | libpng license     | <http://www.libpng.org/pub/png/libpng.html>       |
| libjpeg      | IJG license        | <http://www.ijg.org>                              |
| libwebp      | BSD                | <https://github.com/webmproject/libwebp>          |
| zlib         | zlib               | <https://zlib.net>                                |
| Python       | PSF License        | <https://www.python.org>                          |

### LGPL note

pygame-ce is LGPL v2.1+. The released `.exe` ships the pygame DLLs as
separate files inside the PyInstaller bundle; they remain replaceable, and
upstream source is available at the link above.

## Build-time tool (not bundled)

- **UPX** (<https://upx.github.io>) — used at build time to compress the
  bundled DLLs. UPX is GPL v2+; per the UPX project's stated exception, the
  resulting compressed binary is **not** subject to the GPL. UPX is **not**
  distributed in this repository — download it yourself and place
  `upx.exe` next to `build.cmd` if you want a small build.
