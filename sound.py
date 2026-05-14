"""Procedural sound effects.

A short shuffling 'pscht' for each step: high-pass filtered white noise with
an exponential decay envelope. Synthesised at startup; no audio files needed.
"""
import math
import random
from array import array

import pygame

SAMPLE_RATE = 44100  # match pygame's default; auto-init by pygame.init() uses this


def init_mixer():
    """Ensure pygame.mixer is alive at the rate we generate samples for.
    Returns True on success, False if no audio is available."""
    cur = pygame.mixer.get_init()
    if cur:
        # pygame.init() already brought it up. If the rate disagrees with what
        # we expect, restart the mixer at our rate so playback isn't pitched.
        if cur[0] != SAMPLE_RATE or cur[1] != -16 or cur[2] != 2:
            pygame.mixer.quit()
        else:
            return True
    try:
        pygame.mixer.init(SAMPLE_RATE, -16, 2, 256)
        return True
    except pygame.error:
        return False


def make_pscht(duration=0.14, mid_cutoff_hz=1500, mid_mix=0.35,
               brown_mix=0.85, brown_drive=0.06, brown_leak=0.997,
               envelope_shape=1.2, volume=0.11, seed=None):
    """Synthesise one short dragging shuffle sound.

    Source mix:
      - brown noise (random-walk integrated white) → low-frequency body,
        matches the ~50–300 Hz dominance of the Pixabay reference
      - 1-pole low-passed white at `mid_cutoff_hz` → mid-range scratch
    Envelope is a smooth half-sine swell (sin(πt)^envelope_shape) — rises
    and falls gradually, so the sound reads as a sustained drag rather
    than the percussive attack-then-decay shape that felt choppy.
    """
    rng = random.Random(seed)
    n = int(SAMPLE_RATE * duration)

    # Mid-band low-pass (white noise → ~mid_cutoff_hz roll-off)
    rc = 1.0 / (2 * math.pi * mid_cutoff_hz)
    dt = 1.0 / SAMPLE_RATE
    alpha = dt / (rc + dt)

    samples = array('h')
    lp = 0.0
    brown = 0.0
    for i in range(n):
        x = rng.uniform(-1.0, 1.0)
        # Brown noise: random-walk integrator with a small leak so it doesn't
        # drift away. Heavy low-frequency content, smooth/rumbly character.
        brown = brown * brown_leak + x * brown_drive
        # Low-pass white for the mid-band 'scratch'
        lp += alpha * (x - lp)
        s = brown * brown_mix + lp * mid_mix
        # Smooth swell envelope: zero at both ends, peak in the middle
        phase = (i + 0.5) / n
        env = math.sin(math.pi * phase) ** envelope_shape
        s = max(-1.0, min(1.0, s * env * volume))
        si = int(s * 32767)
        samples.append(si)  # left
        samples.append(si)  # right
    return pygame.mixer.Sound(buffer=samples.tobytes())


def make_pscht_variants(n=5):
    """Pre-generate N slightly different shuffling sounds so repeated steps
    don't sound mechanical. Varies brown/mid mix, cutoff, and envelope."""
    variants = []
    for i in range(n):
        t = i / max(1, n - 1)  # 0..1
        variants.append(make_pscht(
            duration=0.130 + 0.030 * t,                # 130–160 ms
            mid_cutoff_hz=1200 + 600 * (1 - t),        # 1200–1800 Hz
            mid_mix=0.30 + 0.10 * t,                   # 0.30–0.40
            brown_mix=0.75 + 0.20 * (1 - t),           # 0.75–0.95
            brown_drive=0.055 + 0.015 * t,
            envelope_shape=1.0 + 0.5 * t,              # 1.0–1.5
            volume=0.10 + 0.02 * (1 - t),
            seed=i * 7919 + 13,
        ))
    return variants


def play_random(variants):
    if variants:
        random.choice(variants).play()
