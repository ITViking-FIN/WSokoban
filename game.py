"""Sokoban game state and logic. Pure data, no rendering."""
from dataclasses import dataclass, field
from pathlib import Path

WALL = '#'
GOAL = '.'
BOX = '$'
BOX_ON_GOAL = '*'
PLAYER = '@'
PLAYER_ON_GOAL = '+'

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)


@dataclass
class State:
    walls: set
    goals: set
    boxes: set
    player: tuple
    width: int
    height: int
    direction: tuple = DOWN
    moves: int = 0
    pushes: int = 0
    history: list = field(default_factory=list)
    level: int = 1
    used_undo: bool = False  # set True on the first successful undo of this level
    # Cells reachable from the player through non-walls — computed once at
    # level load (the flood is invariant for the level since walls don't
    # change). Used by the renderer to decide which cells get a floor tile.
    reachable: set = field(default_factory=set)

    @property
    def total_packets(self):
        return len(self.goals)

    @property
    def saved_packets(self):
        return len(self.boxes & self.goals)

    def is_solved(self):
        return self.boxes == self.goals

    def move(self, d):
        prev_dir = self.direction
        self.direction = d
        nx, ny = self.player[0] + d[0], self.player[1] + d[1]
        npos = (nx, ny)
        if npos in self.walls:
            return False
        pushed = False
        if npos in self.boxes:
            bx, by = nx + d[0], ny + d[1]
            bpos = (bx, by)
            if bpos in self.walls or bpos in self.boxes:
                return False
            self.boxes.remove(npos)
            self.boxes.add(bpos)
            pushed = True
        self.history.append((d, self.player, pushed, prev_dir))
        self.player = npos
        self.moves += 1
        if pushed:
            self.pushes += 1
        return True

    def undo(self):
        if not self.history:
            return False
        d, prev_player, pushed, prev_dir = self.history.pop()
        if pushed:
            box_to = (self.player[0] + d[0], self.player[1] + d[1])
            box_from = self.player
            self.boxes.discard(box_to)
            self.boxes.add(box_from)
            self.pushes -= 1
        self.moves -= 1
        self.player = prev_player
        self.direction = prev_dir
        self.used_undo = True
        return True

    def snapshot(self):
        return {
            'boxes': list(self.boxes),
            'player': self.player,
            'direction': self.direction,
            'moves': self.moves,
            'pushes': self.pushes,
            'history': list(self.history),
            'used_undo': self.used_undo,
        }

    def restore(self, snap):
        self.boxes = set(tuple(b) for b in snap['boxes'])
        self.player = tuple(snap['player'])
        self.direction = tuple(snap['direction'])
        self.moves = snap['moves']
        self.pushes = snap['pushes']
        self.history = [(tuple(d), tuple(p), pushed, tuple(pd))
                        for d, p, pushed, pd in snap['history']]
        self.used_undo = bool(snap.get('used_undo', False))


def load_level(path, level_num):
    text = Path(path).read_text(encoding='latin-1')
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    walls, goals, boxes = set(), set(), set()
    player = (0, 0)
    width = max(len(l) for l in lines) if lines else 0
    height = len(lines)
    for y, line in enumerate(lines):
        for x, c in enumerate(line):
            if c == WALL:
                walls.add((x, y))
            elif c == GOAL:
                goals.add((x, y))
            elif c == BOX:
                boxes.add((x, y))
            elif c == BOX_ON_GOAL:
                boxes.add((x, y))
                goals.add((x, y))
            elif c == PLAYER:
                player = (x, y)
            elif c == PLAYER_ON_GOAL:
                player = (x, y)
                goals.add((x, y))
    state = State(walls=walls, goals=goals, boxes=boxes, player=player,
                  width=width, height=height, level=level_num)
    state.reachable = _flood_reachable(walls, player, width, height)
    return state


def _flood_reachable(walls, start, width, height):
    """All cells reachable from `start` through non-wall cells, bounded by
    the level dimensions. Computed once per level; the result is invariant
    because walls and bounds don't change during play."""
    seen = set()
    stack = [start]
    while stack:
        p = stack.pop()
        if p in seen or p in walls:
            continue
        x, y = p
        if not (0 <= x < width and 0 <= y < height):
            continue
        seen.add(p)
        stack.append((x + 1, y))
        stack.append((x - 1, y))
        stack.append((x, y + 1))
        stack.append((x, y - 1))
    return seen


def screen_path(screens_dir, level_num):
    return Path(screens_dir) / f'screen.{level_num}'
