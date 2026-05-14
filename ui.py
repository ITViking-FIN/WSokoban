"""Workbench-style chrome and widgets.

Coordinates are in logical (1x) pixels. Display-time scaling renders the
whole logical surface at 2x/3x with nearest-neighbor.
"""
import pygame
import sprites
from sprites import (BG, HILITE, SHADOW, TEXT, DARK, TITLE_STRIPE,
                     STATS_BG, STATS_TEXT)

# ---- Layout (logical pixels) ---------------------------------------------
TILE        = sprites.TILE
PLAY_COLS   = 22
PLAY_ROWS   = 18
PLAY_W      = PLAY_COLS * TILE
PLAY_H      = PLAY_ROWS * TILE

OUTER       = 2
GAP         = 4
PANEL_W     = 152
ROW_H       = 22
BTN_H       = 19

WIN_W = OUTER + GAP + PLAY_W + GAP + PANEL_W + GAP + OUTER
WIN_H = OUTER + GAP + PLAY_H + GAP + ROW_H + GAP + OUTER

PLAY_RECT  = pygame.Rect(OUTER + GAP, OUTER + GAP, PLAY_W, PLAY_H)
PANEL_RECT = pygame.Rect(WIN_W - OUTER - GAP - PANEL_W,
                         OUTER + GAP, PANEL_W, PLAY_H)
ROW_RECT   = pygame.Rect(OUTER + GAP,
                         WIN_H - OUTER - GAP - ROW_H,
                         WIN_W - 2*(OUTER + GAP), ROW_H)


# ---- Fonts ---------------------------------------------------------------
_fonts = {}

def font(name, size, bold=False):
    key = (name, size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont(name, size, bold=bold)
    return _fonts[key]


# ---- Bevels --------------------------------------------------------------
def bevel_out(surf, rect, light=HILITE, dark=SHADOW):
    """Raised bevel: light top/left, dark bottom/right."""
    x, y, w, h = rect
    pygame.draw.line(surf, light, (x, y), (x + w - 1, y))
    pygame.draw.line(surf, light, (x, y), (x, y + h - 1))
    pygame.draw.line(surf, dark, (x, y + h - 1), (x + w - 1, y + h - 1))
    pygame.draw.line(surf, dark, (x + w - 1, y), (x + w - 1, y + h - 1))


def bevel_in(surf, rect, light=HILITE, dark=SHADOW):
    """Sunken bevel: dark top/left, light bottom/right."""
    x, y, w, h = rect
    pygame.draw.line(surf, dark, (x, y), (x + w - 1, y))
    pygame.draw.line(surf, dark, (x, y), (x, y + h - 1))
    pygame.draw.line(surf, light, (x, y + h - 1), (x + w - 1, y + h - 1))
    pygame.draw.line(surf, light, (x + w - 1, y), (x + w - 1, y + h - 1))


# ---- Window chrome -------------------------------------------------------
def draw_window_chrome(surf):
    """Fill the window with the Workbench gray bevel. Title bar is provided
    by the host OS (Windows), so we don't draw one here."""
    surf.fill(BG)
    w, h = surf.get_size()
    # Outer black border on all four sides
    surf.fill(SHADOW, (0, 0, w, 1))
    surf.fill(SHADOW, (0, 0, 1, h))
    surf.fill(SHADOW, (0, h - 1, w, 1))
    surf.fill(SHADOW, (w - 1, 0, 1, h))
    # Inset light/dark bevel
    pygame.draw.line(surf, HILITE, (1, 1), (w - 2, 1))
    pygame.draw.line(surf, HILITE, (1, 1), (1, h - 2))
    pygame.draw.line(surf, DARK,   (1, h - 2), (w - 2, h - 2))
    pygame.draw.line(surf, DARK,   (w - 2, 1), (w - 2, h - 2))


# ---- Button widget -------------------------------------------------------
class Button:
    """Beveled gadget with optional underlined shortcut letter.

    `active=True` renders the button as selected (sunken bevel + blue
    background + white text) — used to indicate which of a pair of
    toggle buttons is currently in effect.
    """

    def __init__(self, label, rect, action, shortcut=None, active=False):
        self.label = label
        self.rect = pygame.Rect(rect)
        self.action = action
        self.shortcut = shortcut  # pygame key code (e.g. pygame.K_n)
        self.pressed = False
        self.hover = False
        self.enabled = True
        self.active = active

    def draw(self, surf, fnt):
        r = self.rect
        # Active = selected toggle state. Blue fill + sunken bevel + white text.
        # Pressed = momentary mouse-down feedback.
        sunken = self.pressed or self.active
        if self.active and not self.pressed:
            pygame.draw.rect(surf, STATS_BG, r)
            text_color = STATS_TEXT
        else:
            pygame.draw.rect(surf, BG, r)
            text_color = TEXT if self.enabled else DARK
        if sunken:
            bevel_in(surf, r)
        else:
            bevel_out(surf, r)
        # Black 1px outer rect for the gadget edge
        pygame.draw.rect(surf, SHADOW, r, 1)
        # Find first occurrence of shortcut letter (case-insensitive)
        letter_idx = -1
        if self.shortcut is not None:
            ch = pygame.key.name(self.shortcut).upper()
            if len(ch) == 1:
                up = self.label.upper()
                letter_idx = up.find(ch)
        text_surf = fnt.render(self.label, True, text_color)
        tx = r.x + (r.w - text_surf.get_width()) // 2
        ty = r.y + (r.h - text_surf.get_height()) // 2
        if self.pressed:
            tx += 1; ty += 1
        surf.blit(text_surf, (tx, ty))
        if letter_idx >= 0:
            prefix_w = fnt.size(self.label[:letter_idx])[0]
            letter_w = fnt.size(self.label[letter_idx])[0]
            uy = ty + text_surf.get_height() - 1
            pygame.draw.line(surf, text_color,
                             (tx + prefix_w, uy),
                             (tx + prefix_w + letter_w - 1, uy))

    def hit(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


# ---- Stats panel ---------------------------------------------------------
def draw_stats_panel(surf, rect, lines):
    pygame.draw.rect(surf, STATS_BG, rect)
    bevel_in(surf, rect)
    f = font('consolas', 12, bold=True)
    lh = f.get_linesize()
    pad_x, pad_y = 6, 4
    y = rect.y + pad_y
    for line in lines:
        ts = f.render(line, True, STATS_TEXT)
        surf.blit(ts, (rect.x + pad_x, y))
        y += lh


# ---- Text field ----------------------------------------------------------
class TextField:
    def __init__(self, rect, value=''):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.focused = False

    def draw(self, surf, fnt):
        pygame.draw.rect(surf, HILITE, self.rect)
        bevel_in(surf, self.rect)
        ts = fnt.render(self.value, True, TEXT)
        clip = surf.get_clip()
        inner = self.rect.inflate(-6, -4)
        surf.set_clip(inner)
        surf.blit(ts, (inner.x, inner.y + (inner.h - ts.get_height()) // 2))
        if self.focused:
            cx = inner.x + ts.get_width() + 1
            pygame.draw.line(surf, TEXT,
                             (cx, inner.y + 2),
                             (cx, inner.y + inner.h - 3))
        surf.set_clip(clip)

    def hit(self, pos):
        return self.rect.collidepoint(pos)

    def handle_key(self, event):
        if event.key == pygame.K_BACKSPACE:
            self.value = self.value[:-1]
        elif event.unicode and event.unicode.isprintable() and len(self.value) < 64:
            self.value += event.unicode


# ---- Playfield rendering -------------------------------------------------
def draw_playfield(surf, state, sp):
    """Draw the play area into PLAY_RECT, centering the level inside it."""
    pygame.draw.rect(surf, BG, PLAY_RECT)
    bevel_in(surf, PLAY_RECT)
    # Center the level within the play area
    off_x = PLAY_RECT.x + (PLAY_RECT.w - state.width * TILE) // 2
    off_y = PLAY_RECT.y + (PLAY_RECT.h - state.height * TILE) // 2

    # Cells that get a floor tile: the cached flood-fill from the player
    # plus any goals/boxes (which are inside by definition).
    inside = state.reachable | state.goals | state.boxes
    walls = state.walls
    goals = state.goals
    boxes = state.boxes
    player = state.player
    direction = state.direction

    for y in range(state.height):
        for x in range(state.width):
            pos = (x, y)
            px, py = off_x + x * TILE, off_y + y * TILE
            if pos in walls:
                surf.blit(sp.wall, (px, py))
                continue
            on_goal = pos in goals
            tile_bg = sp.goal if on_goal else (sp.floor if pos in inside else None)
            if tile_bg is None:
                continue  # leave as workbench gray
            if pos == player:
                surf.blit((sp.eyes_goal if on_goal else sp.eyes_floor)[direction],
                          (px, py))
            elif pos in boxes:
                surf.blit(sp.bag_goal if on_goal else sp.bag_floor, (px, py))
            else:
                surf.blit(tile_bg, (px, py))


# ---- Viewport ------------------------------------------------------------
class Viewport:
    """Maps the fixed-size logical surface onto a resizable display window.
    Preserves aspect ratio with letterbox bars; tracks the scale factor and
    offset so mouse events can be converted back to logical coordinates."""
    def __init__(self):
        self.scale = 1.0
        self.ox = 0
        self.oy = 0

    def to_logical(self, screen_pos):
        if self.scale <= 0:
            return (0, 0)
        return (int((screen_pos[0] - self.ox) / self.scale),
                int((screen_pos[1] - self.oy) / self.scale))

    def present(self, surface):
        display = pygame.display.get_surface()
        sw, sh = display.get_size()
        lw, lh = surface.get_size()
        self.scale = min(sw / lw, sh / lh) if lw and lh else 1.0
        scaled_w = max(1, int(lw * self.scale))
        scaled_h = max(1, int(lh * self.scale))
        self.ox = (sw - scaled_w) // 2
        self.oy = (sh - scaled_h) // 2
        # Black letterbox if the window doesn't match exactly
        if scaled_w != sw or scaled_h != sh:
            display.fill((0, 0, 0))
        if scaled_w == lw and scaled_h == lh:
            display.blit(surface, (self.ox, self.oy))
        else:
            scaled = pygame.transform.scale(surface, (scaled_w, scaled_h))
            display.blit(scaled, (self.ox, self.oy))
        pygame.display.flip()


# ---- Modal dialog frame --------------------------------------------------
def _draw_dialog_frame(surface, rect, title):
    pygame.draw.rect(surface, BG, rect)
    bevel_out(surface, rect)
    pygame.draw.rect(surface, SHADOW, rect, 1)
    tb = pygame.Rect(rect.x + 1, rect.y + 1, rect.w - 2, 14)
    pygame.draw.rect(surface, BG, tb)
    for y in range(tb.top + 2, tb.bottom - 2, 2):
        pygame.draw.line(surface, TITLE_STRIPE,
                         (tb.left + 4, y), (tb.right - 4, y))
    f = font('arial', 11, bold=True)
    ts = f.render(title, True, TEXT)
    bg_rect = ts.get_rect(midleft=(tb.left + 8, tb.centery)).inflate(6, 0)
    pygame.draw.rect(surface, BG, bg_rect)
    surface.blit(ts, (tb.left + 8, tb.centery - ts.get_height() // 2))
    pygame.draw.line(surface, SHADOW,
                     (rect.x + 1, tb.bottom),
                     (rect.right - 2, tb.bottom))
