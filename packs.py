"""Level pack management — discovery, .sok import, per-pack metadata.

A 'pack' is a directory containing screen.1, screen.2, ... files (each
the same plain-text Sokoban grid format used by xsokoban) plus an
optional pack.json with metadata.

Packs live in two places:
  - The built-in 91-level xsokoban set, bundled with the .exe at
    <resource_root>/screens/  — exposed as the 'Original' pack.
  - User-installed packs under <write_root>/packs/<safe_name>/ —
    populated by import_sok_file() or fetched from letslogic.com.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ORIGINAL_PACK = 'Original'
SOKOBAN_CHARS = set('#$.@+* \t')

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


def import_sok_file(src_path: Path, user_dir: Path,
                    fallback_name: str = '') -> PackInfo:
    """Parse a .sok / .xsb / .txt file and write each level out as
    screen.N inside <user_dir>/<pack_name>/. Returns the PackInfo."""
    text = Path(src_path).read_text(encoding='latin-1', errors='replace')
    metadata, levels = parse_sok(text)
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
