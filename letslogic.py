"""letslogic.com API client.

The endpoints are POST with a form-encoded `key=<api_key>` body and
return JSON. The response schema isn't formally documented; this client
probes a handful of common field names so it tolerates minor variation.
If letslogic changes their schema, this is the file to update.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://letslogic.com/api/v1'
DEFAULT_TIMEOUT = 30.0


class APIError(Exception):
    pass


def _post(url: str, params: dict, timeout: float = DEFAULT_TIMEOUT):
    data = urllib.parse.urlencode(params).encode('utf-8')
    req = urllib.request.Request(
        url, data=data, method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded',
                 'Accept': 'application/json',
                 'User-Agent': 'WSokoban'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        raise APIError(f'HTTP {e.code}: {e.reason}') from e
    except urllib.error.URLError as e:
        raise APIError(f'Network error: {e.reason}') from e
    try:
        return json.loads(body)
    except ValueError as e:
        snippet = body[:120].decode('latin-1', errors='replace')
        raise APIError(f'Bad JSON from server: {snippet!r}') from e


def list_collections(api_key: str) -> list[dict]:
    """Return [{id, name, level_count}, ...] for all collections."""
    raw = _post(f'{BASE}/collections', {'key': api_key})
    items = raw if isinstance(raw, list) else (raw.get('collections', []))
    out = []
    for c in items:
        if not isinstance(c, dict):
            continue
        cid = c.get('id') or c.get('collection_id')
        if cid is None:
            continue
        name = (c.get('name') or c.get('title') or f'Collection {cid}')
        count = (c.get('level_count') or c.get('count')
                 or c.get('levels') or c.get('size') or 0)
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 0
        out.append({'id': str(cid), 'name': str(name), 'level_count': count})
    return out


def fetch_collection(api_key: str, collection_id: str
                     ) -> tuple[str, list[list[str]]]:
    """Return (collection_name, [level_grid_lines]) for one collection.

    letslogic.com returns each level as {id, width, height, title, author,
    map, ...} where `map` is a flat width*height string of digits 0-7.
    We translate it back into the standard Sokoban character set.
    """
    raw = _post(f'{BASE}/collection/{collection_id}', {'key': api_key})
    if isinstance(raw, list):
        items = raw
        name = ''
    else:
        items = (raw.get('levels') or raw.get('data')
                 or raw.get('items') or [])
        name = (raw.get('name') or raw.get('collection_name')
                or raw.get('title') or '')
    levels: list[list[str]] = []
    for lv in items:
        if not isinstance(lv, dict):
            continue
        # Preferred shape: digit-encoded `map` + width/height
        m = lv.get('map')
        w = lv.get('width')
        h = lv.get('height')
        if isinstance(m, str) and isinstance(w, int) and isinstance(h, int):
            grid = _decode_map(m, w, h)
        else:
            # Fallback for any shape we haven't seen — try common field names
            data = (lv.get('level_data') or lv.get('data')
                    or lv.get('lines') or lv.get('grid')
                    or lv.get('level') or m or '')
            if isinstance(data, list):
                grid = [str(line) for line in data]
            else:
                grid = str(data).splitlines()
        while grid and not grid[-1].strip():
            grid.pop()
        if grid:
            levels.append(grid)
    return name, levels


# letslogic's digit-encoded tile types → standard Sokoban charset
_TILE = {
    '0': ' ',  # floor
    '1': '#',  # wall
    '2': '@',  # player
    '3': '.',  # goal
    '4': '$',  # box
    '5': '*',  # box on goal
    '6': '+',  # player on goal
    '7': ' ',  # outside the walls
}


def _decode_map(map_str: str, width: int, height: int) -> list[str]:
    """Translate a flat width*height digit string into a list of grid rows
    using the standard Sokoban characters."""
    rows: list[str] = []
    for r in range(height):
        chunk = map_str[r * width:(r + 1) * width]
        if len(chunk) < width:
            chunk = chunk.ljust(width)
        rows.append(''.join(_TILE.get(c, ' ') for c in chunk))
    return rows
