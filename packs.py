"""Level pack management — discovery, multi-format level import,
per-pack metadata.

A 'pack' is a directory containing screen.1, screen.2, ... files (each
the same plain-text Sokoban grid format used by xsokoban) plus an
optional pack.json with metadata.

Packs live in two places:
  - The built-in 91-level xsokoban set, bundled with the .exe at
    <resource_root>/screens/  — exposed as the 'Original' pack.
  - User-installed packs under <write_root>/packs/<safe_name>/ —
    populated by import_collection_file() or fetched from a network
    source (letslogic.com, ...).

Level data comes in several encodings depending on the source. We
canonicalise everything into the standard xsokoban character set
('#', '$', '.', '@', '+', '*', ' ') so the rest of the game only has
to know about one format. The two helpers that do that translation
are exposed here so any future source module (letslogic-style API,
GitHub raw, an HTTP scraper, …) can reuse them:

  - decode_flat_map(map_str, w, h, tile_map): width*height char string
    in any single-char-per-tile encoding → grid rows. Supplied with a
    tile map (LETSLOGIC_TILES, etc.) so the same code handles different
    digit conventions.
  - parse_collection(text): a text blob from a file or HTTP body. Sniffs
    for SLC XML, falls back to .sok / .xsb text parsing. Returns
    (metadata, [(title, rows)]).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ORIGINAL_PACK = 'Original'
SOKOBAN_CHARS = set('#$.@+* \t')

# Tile mappings for digit-encoded level data. Add new entries here when
# another source uses a different convention.
#
# letslogic.com / Sokoban Online: 0=floor, 1=wall, 2=player, 3=goal,
#                                  4=box, 5=box-on-goal, 6=player-on-goal,
#                                  7=outside (treat as floor).
LETSLOGIC_TILES = {
    '0': ' ', '1': '#', '2': '@', '3': '.',
    '4': '$', '5': '*', '6': '+', '7': ' ',
}

_SAFE_NAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass
class PackInfo:
    name: str           # display name
    dir: Path           # directory containing screen.N files
    level_count: int
    author: str = ''
    source: str = ''    # 'builtin', 'imported', 'letslogic'


def safe_pack_name(name: str) -> str:
    """Sanitise an arbitrary string into a directory-safe pack name."""
    name = (name or '').strip()
    name = _SAFE_NAME_RE.sub('', name).strip(' .')
    return name[:64] or 'Imported pack'


def list_packs(builtin_dir: Path, user_dir: Path) -> list[PackInfo]:
    """Return all available packs — Original first, then user packs sorted
    by name."""
    packs: list[PackInfo] = []
    # Built-in
    if builtin_dir.is_dir():
        n = _count_screens(builtin_dir)
        if n > 0:
            packs.append(PackInfo(
                name=ORIGINAL_PACK, dir=builtin_dir,
                level_count=n, author='xsokoban contributors',
                source='builtin'))
    # User
    if user_dir.is_dir():
        user_packs = []
        for sub in sorted(user_dir.iterdir(), key=lambda p: p.name.lower()):
            if not sub.is_dir():
                continue
            meta = _read_meta(sub)
            n = meta.get('level_count') or _count_screens(sub)
            if n <= 0:
                continue
            user_packs.append(PackInfo(
                name=meta.get('name', sub.name),
                dir=sub,
                level_count=int(n),
                author=meta.get('author', ''),
                source=meta.get('source', 'imported'),
            ))
        packs.extend(user_packs)
    return packs


def find_pack(packs: list[PackInfo], name: str) -> PackInfo | None:
    for p in packs:
        if p.name == name:
            return p
    return None


def screen_path(pack: PackInfo, level_num: int) -> Path:
    return pack.dir / f'screen.{level_num}'


def import_collection_file(src_path: Path, user_dir: Path,
                           fallback_name: str = '') -> PackInfo:
    """Read a level-collection file (.sok / .xsb / .txt / .slc) and
    write each level out as screen.N inside <user_dir>/<pack_name>/.
    Format is auto-detected. Returns the PackInfo."""
    text = Path(src_path).read_text(encoding='latin-1', errors='replace')
    metadata, levels = parse_collection(text)
    if not levels:
        raise ValueError('No Sokoban levels found in file.')

    name = (metadata.get('collection')
            or metadata.get('title')
            or fallback_name
            or src_path.stem)
    name = safe_pack_name(name)
    return _write_pack(user_dir, name,
                       levels=[lines for _, lines in levels],
                       author=metadata.get('author', ''),
                       source='imported')


# Old name kept as an alias so external callers still work
import_sok_file = import_collection_file


def install_pack_from_levels(user_dir: Path, name: str,
                             levels: list[list[str]],
                             author: str = '',
                             source: str = 'letslogic') -> PackInfo:
    """Install a pack from a list of pre-parsed level grids (used by the
    letslogic.com API client)."""
    return _write_pack(user_dir, safe_pack_name(name),
                       levels=levels, author=author, source=source)


# ---- Internals -----------------------------------------------------------

def _count_screens(d: Path) -> int:
    """Highest contiguous screen.N number in the directory."""
    n = 0
    while (d / f'screen.{n + 1}').exists():
        n += 1
    return n


def _read_meta(d: Path) -> dict:
    p = d / 'pack.json'
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _write_pack(user_dir: Path, name: str, levels: list[list[str]],
                author: str, source: str) -> PackInfo:
    user_dir.mkdir(parents=True, exist_ok=True)
    target = user_dir / name
    # If a pack with this name exists, suffix with -2, -3, ...
    suffix = 1
    base = target
    while target.exists():
        suffix += 1
        target = user_dir / f'{base.name}-{suffix}'
    target.mkdir()
    for i, lines in enumerate(levels, start=1):
        (target / f'screen.{i}').write_text(
            '\n'.join(lines) + '\n', encoding='latin-1')
    meta = {'name': target.name, 'author': author, 'source': source,
            'level_count': len(levels)}
    (target / 'pack.json').write_text(
        json.dumps(meta, ensure_ascii=False), encoding='utf-8')
    return PackInfo(name=target.name, dir=target,
                    level_count=len(levels),
                    author=author, source=source)


def decode_flat_map(map_str: str, width: int, height: int,
                    tile_map: dict[str, str] = LETSLOGIC_TILES) -> list[str]:
    """Decode a width*height single-char-per-tile string into a list of
    grid rows of standard Sokoban characters. `tile_map` says how each
    source character translates; defaults to the letslogic convention."""
    rows: list[str] = []
    for r in range(height):
        chunk = map_str[r * width:(r + 1) * width]
        if len(chunk) < width:
            chunk = chunk.ljust(width)
        rows.append(''.join(tile_map.get(c, ' ') for c in chunk))
    return rows


def parse_collection(text: str
                     ) -> tuple[dict, list[tuple[str, list[str]]]]:
    """Parse a multi-level collection from a text blob, auto-detecting
    the format. Returns ({metadata}, [(title, rows)]).

    Recognised:
      - .slc (SokobanYASC XML) — `<SokobanLevels>...<Level><L>row</L>...`
      - .sok / .xsb / .txt — plain text with optional 'Key: value' header,
        ';'-prefixed titles, blank-line-separated levels.

    Add a new branch above the .sok fallback when a future format
    needs handling.
    """
    head = text.lstrip()[:200].lower()
    if head.startswith('<?xml') or '<sokobanlevels' in head or '<levelcollection' in head:
        return _parse_slc(text)
    return parse_sok(text)


def parse_sok(text: str) -> tuple[dict, list[tuple[str, list[str]]]]:
    """Parse a .sok / .xsb collection into ({metadata}, [(title, lines)]).

    Tolerant of common dialect variations:
      - 'Key: value' lines at the top become metadata
      - lines starting with ';' are level titles (or comments inside levels)
      - blank lines separate levels
      - any line composed only of Sokoban characters is a map row
    """
    metadata: dict = {}
    levels: list[tuple[str, list[str]]] = []
    current_lines: list[str] = []
    current_title: str | None = None
    seen_first_map = False

    def flush():
        if current_lines:
            title = current_title or f'Level {len(levels) + 1}'
            levels.append((title, current_lines.copy()))
            current_lines.clear()

    for raw in text.splitlines():
        line = raw.rstrip('\r\n')
        stripped = line.strip()
        # Blank line: end of current level
        if not stripped:
            flush()
            current_title = None
            continue
        # Title or comment line
        if stripped.startswith(';'):
            comment = stripped[1:].strip()
            # If we're not currently inside a level, treat as next-level title
            if not current_lines:
                current_title = comment
            continue
        # Metadata line (only meaningful before the first map block)
        if not seen_first_map and ':' in stripped and not _is_map_line(stripped):
            key, _, value = stripped.partition(':')
            metadata[key.strip().lower()] = value.strip()
            continue
        # Map line?
        if _is_map_line(line):
            current_lines.append(line.rstrip())
            seen_first_map = True
            continue
        # Anything else terminates the current level (e.g. unexpected text)
        flush()
        current_title = None
    flush()
    return metadata, levels


def _is_map_line(line: str) -> bool:
    if not line.strip():
        return False
    return all(c in SOKOBAN_CHARS for c in line)


# ---- SLC (SokobanYASC XML) -----------------------------------------------
_LEVEL_RE   = re.compile(r'<Level\b([^>]*)>(.*?)</Level>',
                         re.DOTALL | re.IGNORECASE)
_LINE_RE    = re.compile(r'<L\b[^>]*>(.*?)</L>',
                         re.DOTALL | re.IGNORECASE)
_ATTR_ID    = re.compile(r'Id\s*=\s*"([^"]*)"', re.IGNORECASE)
_COLL_TITLE = re.compile(r'<Title>(.*?)</Title>', re.DOTALL | re.IGNORECASE)
_AUTHOR     = re.compile(r'<(?:Author|Email)>(.*?)</(?:Author|Email)>',
                         re.DOTALL | re.IGNORECASE)


def _xml_unescape(text: str) -> str:
    return (text.replace('&lt;', '<').replace('&gt;', '>')
                .replace('&quot;', '"').replace('&apos;', "'")
                .replace('&amp;', '&'))


def _parse_slc(text: str
               ) -> tuple[dict, list[tuple[str, list[str]]]]:
    """Tiny SLC (SokobanYASC) parser. Regex-based so it doesn't pull
    the `xml` stdlib package into the PyInstaller bundle. Handles the
    common shape:
        <SokobanLevels>
          <Title>...</Title>
          <LevelCollection>
            <Level Id="...">
              <L>map row</L>
              ...
            </Level>
            ...
    """
    metadata: dict = {}
    m = _COLL_TITLE.search(text)
    if m:
        metadata['title'] = _xml_unescape(m.group(1).strip())
    m = _AUTHOR.search(text)
    if m:
        metadata['author'] = _xml_unescape(m.group(1).strip())

    levels: list[tuple[str, list[str]]] = []
    for attrs, body in _LEVEL_RE.findall(text):
        title = ''
        id_match = _ATTR_ID.search(attrs)
        if id_match:
            title = _xml_unescape(id_match.group(1).strip())
        if not title:
            title = f'Level {len(levels) + 1}'
        rows = [_xml_unescape(row).rstrip()
                for row in _LINE_RE.findall(body)]
        # Drop trailing blank rows but keep interior blanks
        while rows and not rows[-1].strip():
            rows.pop()
        if rows:
            levels.append((title, rows))
    return metadata, levels
