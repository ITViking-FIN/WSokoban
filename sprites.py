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
    """Cartoon emoji-style eyes — pill-shaped whites with clean black
    outlines, big pupils that travel all the way to the eye edge in the
    direction of motion, and a catchlight on the *opposite* side of each
    pupil from where it's looking (so it reads as a fixed reflection of
    light from above-left rather than tracking the pupil)."""
    s = base.copy()
    dx, dy = direction
    # Eye dimensions: ODD height matters so the rect has a single true
    # centre row. With eye_h=14 the centre lands between two rows, which
    # made symmetric pdy values (±N) clip on one side and not the other —
    # UP showed a full-circle pupil while DOWN showed a flat-bottom one.
    eye_w, eye_h = 9, 15
    left_rect  = pygame.Rect(0, 0, eye_w, eye_h)
    left_rect.center  = (5, TILE // 2)
    right_rect = pygame.Rect(0, 0, eye_w, eye_h)
    right_rect.center = (14, TILE // 2)
    # Restored to a properly-rounded pill — bigger corner radius that gives
    # an elliptical look top and bottom. The pupil bleed problem is solved
    # by per-eye SRCALPHA masking below rather than by squaring off the
    # corners.
    radius = 5

    # Build a reusable shape mask: opaque rounded-rect, transparent at
    # the rounded-corner background. We'll multiply the pupil's alpha
    # against this so pupil pixels can't draw outside the eye outline.
    mask = pygame.Surface((eye_w, eye_h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255),
                     mask.get_rect(), border_radius=radius)

    # 1. White pill fills
    for r in (left_rect, right_rect):
        pygame.draw.rect(s, EYE_WHITE, r, border_radius=radius)

    # 2. Pupils — 7x7 ellipse (symmetric, unlike pygame.draw.circle at
    # small radii). Drawn on a per-eye temp surface and alpha-multiplied
    # by the eye-shape mask so the pupil always reads as bounded by the
    # rim, even when pushed all the way to the edge.
    pdx = 2 if dx > 0 else (-2 if dx < 0 else 0)
    pdy = 5 if dy > 0 else (-5 if dy < 0 else 0)
    cx_local, cy_local = eye_w // 2, eye_h // 2
    for r in (left_rect, right_rect):
        pupil = pygame.Surface((eye_w, eye_h), pygame.SRCALPHA)
        pygame.draw.ellipse(pupil, EYE_BLACK,
                            pygame.Rect(cx_local + pdx - 3,
                                        cy_local + pdy - 3, 7, 7))
        pupil.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(pupil, r.topleft)

    # 3. Clean 1-pixel outline tracing the same pill shape exactly
    # (same rect, same radius) — no fuzzy edge mismatch.
    for r in (left_rect, right_rect):
        pygame.draw.rect(s, EYE_OUTLINE, r, width=1, border_radius=radius)

    # 4. Black separator between the two whites
    s.fill(EYE_OUTLINE, (9, 4, 2, 13))

    # 5. Catchlight — 2x2 white, on the *opposite* side of the pupil from
    # the direction it's looking. So when the pupil sits at the bottom of
    # the eye, the catchlight is at the top of the pupil; when the pupil
    # is to the right, the catchlight is on its left side; etc.
    for r in (left_rect, right_rect):
        cx, cy = r.center
        px, py = cx + pdx, cy + pdy
        if pdx > 0:
            hx = px - 2          # looking right → highlight on left of pupil
        elif pdx < 0:
            hx = px + 1          # looking left → highlight on right
        else:
            hx = px - 1          # idle horizontally → centered
        if pdy > 0:
            hy = py - 2          # looking down → highlight on top
        elif pdy < 0:
            hy = py + 1          # looking up → highlight on bottom
        else:
            hy = py - 1          # idle vertically → centered
        s.fill(EYE_WHITE, (hx, hy, 2, 2))

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
