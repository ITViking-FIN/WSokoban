"""WSokoban — Windows port of xsokoban (1993), Amiga-styled."""
import json
import math
import random
import re
import sys
from pathlib import Path

import pygame

import game
import sound
import sprites
import ui
from sprites import BG, HILITE, SHADOW, TEXT
from ui import (WIN_W, WIN_H, PLAY_RECT, PANEL_RECT, ROW_RECT, TILE,
                BTN_H, font, bevel_in, bevel_out, Viewport)

VERSION = '1.0.2'

# ---- Paths ---------------------------------------------------------------
def _resource_root():
    """Bundled-asset directory. Inside a PyInstaller --onefile build this is
    the temporary extraction directory (sys._MEIPASS); otherwise it's the
    folder this script lives in."""
    base = getattr(sys, '_MEIPASS', None)
    if base:
        return Path(base)
    return Path(__file__).parent


def _write_root():
    """Where save files should live. Next to the .exe when frozen, else
    next to this script — so saves persist across runs."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


ROOT = _write_root()
RESOURCE_ROOT = _resource_root()
SCREENS_DIR = RESOURCE_ROOT / 'screens'
SCORES_PATH = ROOT / 'WSokoban.scores'
SETTINGS_PATH = ROOT / 'WSokoban.settings'
DEFAULT_SAVE_NAME = 'WSokoban.data'

NUM_LEVELS = 91


# ---- Layout helpers ------------------------------------------------------
def panel_button_rects():
    """Return rects for the right-side panel buttons.

    Order (top to bottom): New, Undo, Set Level, High Scores, About,
    [stats panel], Backup, Restore.
    """
    p = PANEL_RECT
    pad = 4
    x = p.x + pad
    w = p.w - 2 * pad
    half_w = (w - 4) // 2
    y = p.y + pad

    rects = {}
    # New | Undo paired
    rects['new']  = pygame.Rect(x,                  y, half_w, BTN_H)
    rects['undo'] = pygame.Rect(x + half_w + 4,     y, w - half_w - 4, BTN_H)
    y += BTN_H + 4
    rects['setlvl'] = pygame.Rect(x, y, w, BTN_H); y += BTN_H + 4
    rects['hi']     = pygame.Rect(x, y, w, BTN_H); y += BTN_H + 4
    rects['about']  = pygame.Rect(x, y, w, BTN_H); y += BTN_H + 6

    # Stats panel: 5 lines of monospace bold ~12pt
    stats_h = 5 * 14 + 14
    rects['stats'] = pygame.Rect(x, y, w, stats_h); y += stats_h + 6

    rects['backup']  = pygame.Rect(x, y, w, BTN_H); y += BTN_H + 4
    rects['restore'] = pygame.Rect(x, y, w, BTN_H); y += BTN_H + 6

    # Sound FX toggle (two stacked buttons, the active one stays highlighted)
    rects['fx_on']  = pygame.Rect(x, y, w, BTN_H); y += BTN_H + 4
    rects['fx_off'] = pygame.Rect(x, y, w, BTN_H); y += BTN_H + 4
    return rects


def row_button_rects():
    """Rects for the bottom row: Name | filename field | Load | Save."""
    r = ROW_RECT
    pad = 0
    name_w = 48
    save_w = 48
    load_w = 48
    field_w = r.w - name_w - load_w - save_w - 4 * 3
    x = r.x
    rects = {}
    rects['name']  = pygame.Rect(x, r.y + 1, name_w, r.h - 2); x += name_w + 4
    rects['field'] = pygame.Rect(x, r.y + 1, field_w, r.h - 2); x += field_w + 4
    rects['load']  = pygame.Rect(x, r.y + 1, load_w, r.h - 2); x += load_w + 4
    rects['save']  = pygame.Rect(x, r.y + 1, save_w, r.h - 2)
    return rects


# ---- Persistence ---------------------------------------------------------
_FILENAME_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_save_path(name):
    """Resolve `name` to a path inside ROOT, refusing path traversal and
    Windows-illegal characters. Falls back to DEFAULT_SAVE_NAME if the
    sanitised name ends up empty."""
    if not name:
        name = DEFAULT_SAVE_NAME
    # Take only the bare filename — defeats both `..\..\evil.txt` and any
    # absolute path the user might have typed in the field.
    name = Path(name).name
    name = _FILENAME_INVALID.sub('', name).strip(' .')
    if not name:
        name = DEFAULT_SAVE_NAME
    return ROOT / name[:64]


def _apply_snapshot(state, snap):
    """Mutate `state` in place from a save-file dict. Raises on bad data."""
    state.boxes = set(tuple(b) for b in snap['boxes'])
    state.player = tuple(snap['player'])
    state.direction = tuple(snap['direction'])
    state.moves = int(snap['moves'])
    state.pushes = int(snap['pushes'])
    state.history = [(tuple(d), tuple(p), bool(pu), tuple(pd))
                     for d, p, pu, pd in snap.get('history', [])]
    state.used_undo = bool(snap.get('used_undo', False))


def save_game(state, path):
    data = {
        'level': state.level,
        'player': list(state.player),
        'direction': list(state.direction),
        'boxes': [list(b) for b in state.boxes],
        'moves': state.moves,
        'pushes': state.pushes,
        'used_undo': state.used_undo,
        'history': [[list(d), list(p), pushed, list(pd)]
                    for d, p, pushed, pd in state.history],
    }
    Path(path).write_text(json.dumps(data))


def load_game(path):
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
    return data


def load_scores():
    try:
        return json.loads(SCORES_PATH.read_text())
    except (OSError, ValueError):
        return {}


def save_scores(scores):
    SCORES_PATH.write_text(json.dumps(scores))


def load_settings():
    try:
        return json.loads(SETTINGS_PATH.read_text())
    except (OSError, ValueError):
        return {}


def save_settings(settings):
    SETTINGS_PATH.write_text(json.dumps(settings))


def record_score(scores, level, moves, pushes, clean):
    """Record a level completion. `clean` is True when the player solved
    the level without ever pressing Undo."""
    key = str(level)
    entries = scores.setdefault(key, [])
    entries.append([moves, pushes, 1 if clean else 0])
    # Sort by (moves, pushes); the clean flag is informational, not a tiebreaker.
    entries.sort(key=lambda e: (e[0], e[1]))
    scores[key] = entries[:5]
    save_scores(scores)


# ---- App state -----------------------------------------------------------
class App:
    def __init__(self):
        self.scale = 2
        self.scores = load_scores()
        self.settings = load_settings()
        self.sound_enabled = bool(self.settings.get('sound', True))
        self.save_filename = DEFAULT_SAVE_NAME
        self.backup = None
        self.state = None
        self._init_state()

    def set_sound(self, on):
        self.sound_enabled = bool(on)
        self.settings['sound'] = self.sound_enabled
        save_settings(self.settings)

    def _init_state(self):
        # Try to resume from default save file
        snap = load_game(safe_save_path(self.save_filename))
        if snap and 1 <= snap.get('level', 0) <= NUM_LEVELS:
            self.state = game.load_level(
                game.screen_path(SCREENS_DIR, snap['level']), snap['level'])
            try:
                _apply_snapshot(self.state, snap)
            except (KeyError, ValueError, TypeError):
                self.load_level(1)
        else:
            self.load_level(1)

    def load_level(self, n):
        n = max(1, min(NUM_LEVELS, n))
        self.state = game.load_level(game.screen_path(SCREENS_DIR, n), n)
        self.backup = None

    def reset_level(self):
        self.load_level(self.state.level)

    def next_level(self):
        if self.state.level < NUM_LEVELS:
            self.load_level(self.state.level + 1)


# ---- Modals --------------------------------------------------------------
_DIM_CACHE = {}


def dim_under(surface):
    """Darken the whole surface for a modal underlay. Reuses a single
    SRCALPHA overlay per logical-surface size — modals call this every
    frame and the per-frame allocation was burning ~1 MB/frame."""
    key = surface.get_size()
    overlay = _DIM_CACHE.get(key)
    if overlay is None:
        overlay = pygame.Surface(key, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 80))
        _DIM_CACHE[key] = overlay
    surface.blit(overlay, (0, 0))


def dialog_rect(w, h):
    return pygame.Rect((WIN_W - w) // 2, (WIN_H - h) // 2, w, h)


def _handle_resize_event(event):
    """If the event is a resize and the new size differs from the current
    display, push it to the display. Skipping no-op resizes prevents flicker
    and wasted work during a drag-resize that emits redundant events."""
    if event.type == pygame.VIDEORESIZE:
        new_w = max(200, event.w)
        new_h = max(150, event.h)
        cur = pygame.display.get_surface()
        if cur is None or cur.get_size() != (new_w, new_h):
            pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)


CONFETTI_COLORS = [
    (255,  70,  70),  # red
    (255, 150,  50),  # orange
    (255, 220,  60),  # yellow
    ( 90, 220,  90),  # green
    ( 80, 150, 255),  # blue
    (180, 100, 230),  # purple
    (255, 130, 200),  # pink
    (100, 220, 220),  # cyan
]


def play_confetti(surface, viewport, state, frames=80, n_particles=90):
    """Animate a confetti burst from the player's position. Blocks for
    ~`frames`/60 seconds then returns. The current contents of `surface`
    are used as the static background for every frame of the animation."""
    # Player tile center in surface (logical) coords
    off_x = PLAY_RECT.x + (PLAY_RECT.w - state.width * TILE) // 2
    off_y = PLAY_RECT.y + (PLAY_RECT.h - state.height * TILE) // 2
    cx = off_x + state.player[0] * TILE + TILE // 2
    cy = off_y + state.player[1] * TILE + TILE // 2

    # Each particle: [x, y, vx, vy, color, w, h]
    particles = []
    for _ in range(n_particles):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.8, 5.5)
        particles.append([
            float(cx), float(cy),
            math.cos(angle) * speed,
            math.sin(angle) * speed - 2.0,           # bias upward for the burst
            random.choice(CONFETTI_COLORS),
            random.randint(2, 4),                     # width
            random.randint(2, 4),                     # height
        ])

    snapshot = surface.copy()
    clock = pygame.time.Clock()
    GRAVITY = 0.22
    DRAG = 0.995

    for f in range(frames):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            _handle_resize_event(event)
        # Step physics
        for p in particles:
            p[3] += GRAVITY
            p[2] *= DRAG
            p[0] += p[2]
            p[1] += p[3]
        # Draw
        surface.blit(snapshot, (0, 0))
        for p in particles:
            pygame.draw.rect(surface, p[4],
                             (int(p[0]), int(p[1]), p[5], p[6]))
        viewport.present(surface)
        clock.tick(60)


def message_dialog(surface, viewport, title, lines, buttons=('OK',)):
    """Show a centered modal with lines of text and one or more buttons.
    Returns the label of the clicked button, or 'cancel' on Esc/close."""
    fnt = font('arial', 11, bold=True)
    line_h = fnt.get_linesize()
    text_w = max(fnt.size(l)[0] for l in lines) if lines else 0
    btn_w = max(60, max(fnt.size(b)[0] + 16 for b in buttons))
    total_btn_w = btn_w * len(buttons) + 6 * (len(buttons) - 1)
    body_w = max(text_w, total_btn_w) + 32
    body_h = 22 + len(lines) * line_h + 16 + BTN_H + 12
    rect = dialog_rect(max(220, body_w), max(90, body_h))

    # Build button rects
    btn_rects = []
    btn_y = rect.bottom - BTN_H - 8
    btn_x = rect.right - 8 - total_btn_w
    for label in buttons:
        br = pygame.Rect(btn_x, btn_y, btn_w, BTN_H)
        btn_rects.append((label, br))
        btn_x += btn_w + 6

    snapshot = surface.copy()
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'quit'
            _handle_resize_event(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return 'cancel'
                if event.key == pygame.K_RETURN:
                    return buttons[0]
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = viewport.to_logical(event.pos)
                for label, br in btn_rects:
                    if br.collidepoint(mx, my):
                        return label
        # Draw
        surface.blit(snapshot, (0, 0))
        dim_under(surface)
        ui._draw_dialog_frame(surface, rect, title)
        ty = rect.y + 22
        for line in lines:
            ts = fnt.render(line, True, TEXT)
            surface.blit(ts, (rect.x + 16, ty))
            ty += line_h
        for label, br in btn_rects:
            pygame.draw.rect(surface, BG, br)
            bevel_out(surface, br)
            pygame.draw.rect(surface, SHADOW, br, 1)
            ts = fnt.render(label, True, TEXT)
            surface.blit(ts, (br.x + (br.w - ts.get_width()) // 2,
                              br.y + (br.h - ts.get_height()) // 2))
        viewport.present(surface)
        clock.tick(60)


def input_dialog(surface, viewport, title, prompt, default=''):
    """Modal with a text input. Returns the string or None on cancel."""
    fnt = font('arial', 11, bold=True)
    rect = dialog_rect(260, 100)
    field = ui.TextField(pygame.Rect(rect.x + 16, rect.y + 42,
                                     rect.w - 32, 18), default)
    field.focused = True
    btn_w = 60
    ok = pygame.Rect(rect.right - btn_w * 2 - 14, rect.bottom - BTN_H - 8,
                     btn_w, BTN_H)
    cancel = pygame.Rect(rect.right - btn_w - 8, rect.bottom - BTN_H - 8,
                         btn_w, BTN_H)
    snapshot = surface.copy()
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            _handle_resize_event(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_RETURN:
                    return field.value
                field.handle_key(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = viewport.to_logical(event.pos)
                if ok.collidepoint(mx, my):
                    return field.value
                if cancel.collidepoint(mx, my):
                    return None
        surface.blit(snapshot, (0, 0))
        dim_under(surface)
        ui._draw_dialog_frame(surface, rect, title)
        ts = fnt.render(prompt, True, TEXT)
        surface.blit(ts, (rect.x + 16, rect.y + 24))
        field.draw(surface, fnt)
        for label, br in (('OK', ok), ('Cancel', cancel)):
            pygame.draw.rect(surface, BG, br)
            bevel_out(surface, br)
            pygame.draw.rect(surface, SHADOW, br, 1)
            ts = fnt.render(label, True, TEXT)
            surface.blit(ts, (br.x + (br.w - ts.get_width()) // 2,
                              br.y + (br.h - ts.get_height()) // 2))
        viewport.present(surface)
        clock.tick(60)


def high_scores_dialog(surface, viewport, scores):
    fnt = font('consolas', 12, bold=True)
    line_h = fnt.get_linesize()
    rect = dialog_rect(300, 280)
    list_rect = pygame.Rect(rect.x + 12, rect.y + 24, rect.w - 24, rect.h - 60)
    btn = pygame.Rect(rect.right - 70, rect.bottom - BTN_H - 8, 60, BTN_H)

    # Build the displayed lines. Clean = solved without any Undo (shown as '*').
    lines = ['Lvl  Moves Pushes  Clean']
    for n in range(1, NUM_LEVELS + 1):
        entries = scores.get(str(n))
        if not entries:
            continue
        e = entries[0]
        m, p = e[0], e[1]
        # Backward compat: old entries are 2-tuples and don't have a flag.
        if len(e) >= 3:
            mark = '  *  ' if e[2] else '     '
        else:
            mark = '  ?  '
        lines.append(f'{n:>3}  {m:>5} {p:>5}  {mark}')
    if len(lines) == 1:
        lines.append(' ')
        lines.append(' (no scores yet)')

    scroll = 0
    visible_lines = list_rect.h // line_h
    max_scroll = max(0, len(lines) - visible_lines)
    snapshot = surface.copy()
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'quit'
            _handle_resize_event(event)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    return 'ok'
                if event.key == pygame.K_DOWN:
                    scroll = min(scroll + 1, max_scroll)
                if event.key == pygame.K_UP:
                    scroll = max(scroll - 1, 0)
                if event.key == pygame.K_PAGEDOWN:
                    scroll = min(scroll + visible_lines, max_scroll)
                if event.key == pygame.K_PAGEUP:
                    scroll = max(scroll - visible_lines, 0)
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = viewport.to_logical(event.pos)
                if event.button == 1 and btn.collidepoint(mx, my):
                    return 'ok'
                if event.button == 4:
                    scroll = max(scroll - 3, 0)
                if event.button == 5:
                    scroll = min(scroll + 3, max_scroll)
        surface.blit(snapshot, (0, 0))
        dim_under(surface)
        ui._draw_dialog_frame(surface, rect, 'High Scores')
        pygame.draw.rect(surface, HILITE, list_rect)
        bevel_in(surface, list_rect)
        clip = surface.get_clip()
        inner = list_rect.inflate(-6, -4)
        surface.set_clip(inner)
        y = inner.y - scroll * line_h
        for i, line in enumerate(lines):
            ts = fnt.render(line, True, TEXT)
            surface.blit(ts, (inner.x, y))
            y += line_h
        surface.set_clip(clip)
        pygame.draw.rect(surface, BG, btn)
        bevel_out(surface, btn)
        pygame.draw.rect(surface, SHADOW, btn, 1)
        bf = font('arial', 11, bold=True)
        ts = bf.render('OK', True, TEXT)
        surface.blit(ts, (btn.x + (btn.w - ts.get_width()) // 2,
                          btn.y + (btn.h - ts.get_height()) // 2))
        viewport.present(surface)
        clock.tick(60)


# ---- Main loop -----------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption(f'WSokoban {VERSION}')
    icon_path = RESOURCE_ROOT / 'icon.png'
    if icon_path.exists():
        pygame.display.set_icon(pygame.image.load(str(icon_path)))
    app = App()

    # Audio: initialise mixer and pre-generate footstep variants. If audio
    # init fails (e.g. no sound device), we silently degrade — game still works.
    pscht_sounds = []
    if sound.init_mixer():
        try:
            pscht_sounds = sound.make_pscht_variants(5)
        except pygame.error:
            pscht_sounds = []

    # Open the window resizable; start at 2x scale.
    pygame.display.set_mode((WIN_W * app.scale, WIN_H * app.scale),
                            pygame.RESIZABLE)
    surface = pygame.Surface((WIN_W, WIN_H))
    sp = sprites.Sprites()
    viewport = Viewport()

    panel_rects = panel_button_rects()
    row_rects = row_button_rects()

    # Build button widgets
    btns = {
        'new':     ui.Button('New',         panel_rects['new'],     'new',     pygame.K_n),
        'undo':    ui.Button('Undo',        panel_rects['undo'],    'undo',    pygame.K_u),
        'setlvl':  ui.Button('Set Level',   panel_rects['setlvl'],  'setlvl',  pygame.K_l),
        'hi':      ui.Button('High Scores', panel_rects['hi'],      'hi',      pygame.K_h),
        'about':   ui.Button('About',       panel_rects['about'],   'about',   pygame.K_a),
        'backup':  ui.Button('Backup',      panel_rects['backup'],  'backup',  pygame.K_b),
        'restore': ui.Button('Restore',     panel_rects['restore'], 'restore', pygame.K_r),
        'fx_on':   ui.Button('Sound FX ON', panel_rects['fx_on'],   'fx_on',   None),
        'fx_off':  ui.Button('Sound FX OFF',panel_rects['fx_off'],  'fx_off',  None),
        'name':    ui.Button('Name',        row_rects['name'],      'name',    None),
        'load':    ui.Button('Load',        row_rects['load'],      'load',    None),
        'save':    ui.Button('Save',        row_rects['save'],      'save',    pygame.K_s),
    }
    field = ui.TextField(row_rects['field'], app.save_filename)

    bf = font('arial', 11, bold=True)

    clock = pygame.time.Clock()
    running = True
    pressed_btn = None  # key for visual press feedback

    def play_step():
        if app.sound_enabled and pscht_sounds:
            sound.play_random(pscht_sounds)

    def try_move(d):
        if app.state.move(d):
            play_step()

    def do_action(action):
        st = app.state
        if action == 'new':
            app.reset_level()
        elif action == 'undo':
            st.undo()
        elif action == 'setlvl':
            v = input_dialog(surface, viewport, 'Set Level',
                             f'Level (1-{NUM_LEVELS}):', str(st.level))
            if v is not None:
                try:
                    app.load_level(int(v))
                except ValueError:
                    pass
        elif action == 'hi':
            high_scores_dialog(surface, viewport, app.scores)
        elif action == 'about':
            message_dialog(surface, viewport, 'About',
                           [f'WSokoban {VERSION}',
                            '',
                            'Port of xsokoban (1989, A. Myers et al.)',
                            'Inspired by the Amiga port by',
                            'Panagiotis Christias (1993).',
                            '',
                            'Public domain. 91 levels.'])
        elif action == 'backup':
            app.backup = st.snapshot()
        elif action == 'restore':
            if app.backup:
                st.restore(app.backup)
        elif action == 'fx_on':
            app.set_sound(True)
        elif action == 'fx_off':
            app.set_sound(False)
        elif action == 'name':
            v = input_dialog(surface, viewport, 'Save File',
                             'Filename:', field.value)
            if v:
                field.value = v
                app.save_filename = v
        elif action == 'save':
            app.save_filename = field.value or DEFAULT_SAVE_NAME
            path = safe_save_path(app.save_filename)
            save_game(st, path)
            message_dialog(surface, viewport, 'Saved',
                           [f'Saved to {path.name}.'])
        elif action == 'load':
            app.save_filename = field.value or DEFAULT_SAVE_NAME
            path = safe_save_path(app.save_filename)
            snap = load_game(path)
            if snap is None:
                message_dialog(surface, viewport, 'Load',
                               [f'Could not read {path.name}.'])
            else:
                try:
                    app.load_level(snap['level'])
                    _apply_snapshot(app.state, snap)
                except (KeyError, ValueError, TypeError):
                    message_dialog(surface, viewport, 'Load',
                                   ['Save file is corrupt.'])

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            _handle_resize_event(event)
            if event.type == pygame.KEYDOWN:
                if field.focused:
                    if event.key == pygame.K_RETURN:
                        field.focused = False
                        app.save_filename = field.value or DEFAULT_SAVE_NAME
                    elif event.key == pygame.K_ESCAPE:
                        field.focused = False
                    else:
                        field.handle_key(event)
                    continue
                k = event.key
                if k == pygame.K_q:
                    running = False
                elif k == pygame.K_UP:
                    try_move(game.UP)
                elif k == pygame.K_DOWN:
                    try_move(game.DOWN)
                elif k == pygame.K_LEFT:
                    try_move(game.LEFT)
                elif k == pygame.K_RIGHT:
                    try_move(game.RIGHT)
                elif k == pygame.K_PLUS or k == pygame.K_EQUALS:
                    new_scale = min(int(round(viewport.scale)) + 1, 4)
                    pygame.display.set_mode((WIN_W * new_scale,
                                             WIN_H * new_scale),
                                            pygame.RESIZABLE)
                elif k == pygame.K_MINUS:
                    new_scale = max(int(round(viewport.scale)) - 1, 1)
                    pygame.display.set_mode((WIN_W * new_scale,
                                             WIN_H * new_scale),
                                            pygame.RESIZABLE)
                else:
                    # Button shortcuts
                    for b in btns.values():
                        if b.shortcut == k and b.enabled:
                            do_action(b.action)
                            break
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = viewport.to_logical(event.pos)
                field.focused = field.hit(pos)
                for key, b in btns.items():
                    if b.hit(pos):
                        b.pressed = True
                        pressed_btn = key
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if pressed_btn:
                    b = btns[pressed_btn]
                    b.pressed = False
                    pos = viewport.to_logical(event.pos)
                    if b.hit(pos):
                        do_action(b.action)
                    pressed_btn = None

        # Win check (after handling input)
        if app.state.is_solved():
            clean = not app.state.used_undo
            record_score(app.scores, app.state.level,
                         app.state.moves, app.state.pushes, clean)
            # Confetti burst from the player's tile, then the dialog.
            # Re-draw everything once so the snapshot the animation uses is
            # current, then run the burst.
            ui.draw_window_chrome(surface)
            ui.draw_playfield(surface, app.state, sp)
            for key in ('new', 'undo', 'setlvl', 'hi', 'about',
                        'backup', 'restore', 'fx_on', 'fx_off'):
                btns[key].draw(surface, bf)
            ui.draw_stats_panel(surface, panel_rects['stats'], [
                f'Level   {app.state.level:02d}',
                f'Packets {app.state.total_packets:02d}',
                f'Saved   {app.state.saved_packets:02d}',
                f'Moves   {app.state.moves:04d}',
                f'Pushes  {app.state.pushes:04d}',
            ])
            for key in ('name', 'load', 'save'):
                btns[key].draw(surface, bf)
            field.draw(surface, bf)
            play_confetti(surface, viewport, app.state)

            lines = [f'Level {app.state.level} solved!',
                     f'Moves: {app.state.moves}   Pushes: {app.state.pushes}']
            lines.append('Clean run (no Undo used)!' if clean
                         else 'Solved with Undo.')
            answer = message_dialog(surface, viewport, 'Solved!',
                                    lines, buttons=('Next', 'Retry'))
            if answer == 'Retry':
                app.reset_level()
            else:
                app.next_level()

        # Sync FX toggle visual state to actual setting
        btns['fx_on'].active  = app.sound_enabled
        btns['fx_off'].active = not app.sound_enabled

        # ---- Draw ------------------------------------------------------
        ui.draw_window_chrome(surface)
        ui.draw_playfield(surface, app.state, sp)

        # Right panel
        for key in ('new', 'undo', 'setlvl', 'hi', 'about',
                    'backup', 'restore', 'fx_on', 'fx_off'):
            btns[key].draw(surface, bf)

        # Stats panel
        st = app.state
        stats_lines = [
            f'Level   {st.level:02d}',
            f'Packets {st.total_packets:02d}',
            f'Saved   {st.saved_packets:02d}',
            f'Moves   {st.moves:04d}',
            f'Pushes  {st.pushes:04d}',
        ]
        ui.draw_stats_panel(surface, panel_rects['stats'], stats_lines)

        # Bottom row
        for key in ('name', 'load', 'save'):
            btns[key].draw(surface, bf)
        field.draw(surface, bf)

        viewport.present(surface)
        clock.tick(60)

    # Auto-save on exit
    save_game(app.state, safe_save_path(app.save_filename))
    pygame.quit()


if __name__ == '__main__':
    main()
