"""Procedural pixel-art tiles for the Amiga Sokoban look.

Drawn at native (1x) resolution into pygame Surfaces. Display-time scaling
with nearest-neighbor preserves the chunky look.
"""
import pygame
from game import UP, DOWN, LEFT, RIGHT

TILE = 20

# Workbench / Amiga palette
BG          = (170, 170, 170)
HILITE      = (255, 255, 255)
SHADOW      = (0,   0,   0)
TEXT        = (0,   0,   0)
DARK        = (102, 102, 102)
TITLE_STRIPE= (102, 102, 136)

WALL_HI     = (180, 195, 220)
WALL        = (118, 138, 175)
WALL_LO     = (62,  82,  120)
WALL_GROUT  = (40,  55,  85)

FLOOR       = (170, 170, 170)
GOAL_BG     = (88,  124, 176)
GOAL_DARK   = (60,  88,  130)

BAG_HI      = (235, 222, 188)
BAG         = (210, 190, 145)
BAG_LO      = (155, 125, 85)
BAG_OUT     = (85,  60,  35)

EYE_WHITE   = (245, 245, 245)
EYE_BLACK   = (10,  10,  10)
EYE_OUTLINE = (0,   0,   0)

STATS_BG    = (88,  124, 176)
STATS_TEXT  = (255, 255, 255)


def _wall_tile():
    s = pygame.Surface((TILE, TILE))
    # Thin grout border on all 4 sides
    s.fill(WALL_GROUT)
    inner = pygame.Rect(1, 1, TILE - 2, TILE - 2)
    s.fill(WALL, inner)
    # Top + left highlight
    pygame.draw.line(s, WALL_HI, (1, 1), (TILE - 2, 1))
    pygame.draw.line(s, WALL_HI, (1, 1), (1, TILE - 2))
    # Bottom + right shadow
    pygame.draw.line(s, WALL_LO, (1, TILE - 2), (TILE - 2, TILE - 2))
    pygame.draw.line(s, WALL_LO, (TILE - 2, 1), (TILE - 2, TILE - 2))
    # Faint horizontal seam mid-tile for cinder-block feel
    pygame.draw.line(s, WALL_LO, (3, TILE // 2), (TILE - 4, TILE // 2))
    pygame.draw.line(s, WALL_HI, (3, TILE // 2 + 1), (TILE - 4, TILE // 2 + 1))
    return s


def _floor_tile():
    s = pygame.Surface((TILE, TILE))
    s.fill(FLOOR)
    return s


def _goal_tile():
    s = pygame.Surface((TILE, TILE))
    s.fill(GOAL_BG)
    return s


def _moneybag(base):
    """Burlap drawstring sack — rounded shoulders, flat bottom, € sign."""
    if not pygame.font.get_init():
        pygame.font.init()
    s = base.copy()
    cx = TILE // 2  # 10

    # Body: 16 wide x 13 tall, x=2..17, y=6..18 — leaves room for tied top
    body = pygame.Rect(2, 6, 16, 13)

    # Body fill — rounded shoulders, nearly-flat bottom
    pygame.draw.rect(s, BAG, body,
                     border_top_left_radius=5, border_top_right_radius=5,
                     border_bottom_left_radius=1, border_bottom_right_radius=1)
    # Outline
    pygame.draw.rect(s, BAG_OUT, body, width=1,
                     border_top_left_radius=5, border_top_right_radius=5,
                     border_bottom_left_radius=1, border_bottom_right_radius=1)

    # Highlight on upper-left of body
    pygame.draw.rect(s, BAG_HI, (body.left + 2, body.top + 2, 4, 3))
    # Subtle shadow on lower-right to add volume
    pygame.draw.rect(s, BAG_LO, (body.right - 5, body.bottom - 4, 3, 2))
    # Crease line below the cinch
    pygame.draw.line(s, BAG_LO,
                     (body.left + 4, body.top + 1),
                     (body.right - 5, body.top + 1))

    # Tied band right above body
    band = pygame.Rect(cx - 3, body.top - 3, 6, 3)
    pygame.draw.rect(s, BAG_LO, band)
    pygame.draw.rect(s, BAG_OUT, band, width=1)

    # Cinched fabric tuft above the band
    tuft = pygame.Rect(cx - 2, band.top - 3, 4, 3)
    pygame.draw.ellipse(s, BAG_OUT, tuft.inflate(2, 1))
    pygame.draw.ellipse(s, BAG_LO, tuft)

    # € sign on the body
    e_font = pygame.font.SysFont('arial', 12, bold=True)
    e_surf = e_font.render('€', False, BAG_OUT)
    e_rect = e_surf.get_rect(center=(cx, body.centery + 1))
    s.blit(e_surf, e_rect)

    return s


def _eyes(base, direction):
    """Draw a pair of vertical-oval eyes filling most of the tile,
    pupils shifted toward direction of motion."""
    s = base.copy()
    dx, dy = direction
    # Two oval eyes side by side, filling most of the 20x20 tile
    eye_w, eye_h = 9, 14
    left_rect  = pygame.Rect(0, 0, eye_w, eye_h)
    left_rect.center  = (5, TILE // 2)
    right_rect = pygame.Rect(0, 0, eye_w, eye_h)
    right_rect.center = (14, TILE // 2)
    # Capsule/pill shape: round top + bottom corners, flat vertical sides.
    # Using draw.rect with a corner radius gives flatter sides than the
    # full ellipse the previous version drew.
    radius = 4
    for r in (left_rect, right_rect):
        pygame.draw.rect(s, EYE_OUTLINE, r.inflate(2, 2),
                         border_radius=radius + 1)
    for r in (left_rect, right_rect):
        pygame.draw.rect(s, EYE_WHITE, r, border_radius=radius)
    # Black separator down the middle so the two whites read as distinct eyes
    s.fill(EYE_OUTLINE, (9, 4, 2, 12))
    # Pupils: large filled circles like the 👀 emoji — pupil takes most of
    # the eye, leaving only a thin white ring. A small white catchlight in
    # the upper-left of the pupil sells the glossy look.
    pdx = 1 if dx > 0 else (-1 if dx < 0 else 0)
    pdy = 3 if dy > 0 else (-3 if dy < 0 else 0)
    for r in (left_rect, right_rect):
        cx, cy = r.center
        px, py = cx + pdx, cy + pdy
        pygame.draw.circle(s, EYE_BLACK, (px, py), 3)
        # Catchlight: 2x2 white pixel cluster, upper-left of pupil
        s.fill(EYE_WHITE, (px - 2, py - 2, 2, 2))
    return s


class Sprites:
    """Pre-rendered tile surfaces. Build once."""

    def __init__(self):
        self.wall  = _wall_tile()
        self.floor = _floor_tile()
        self.goal  = _goal_tile()

        self.bag_floor = _moneybag(self.floor)
        self.bag_goal  = _moneybag(self.goal)

        self.eyes_floor = {d: _eyes(self.floor, d) for d in (UP, DOWN, LEFT, RIGHT)}
        self.eyes_goal  = {d: _eyes(self.goal,  d) for d in (UP, DOWN, LEFT, RIGHT)}
