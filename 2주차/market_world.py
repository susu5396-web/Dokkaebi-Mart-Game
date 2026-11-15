"""긴 매대 다섯 개와 넓은 통로. 모든 좌표는 좌상단 원점이다."""
from dataclasses import dataclass

WORLD_W, WORLD_H = 2200, 2240
SHELF_TOP, SHELF_HEIGHT, SHELF_WIDTH = 200, 1680, 200
SECTION_HEIGHT = SHELF_HEIGHT / 8
SHELVES = tuple((200 + i * 400, SHELF_TOP, SHELF_WIDTH, SHELF_HEIGHT)
                for i in range(5))
CHECKOUT = (65, 2040, 240, 130)
AISLE_CENTERS = tuple(100 + i * 400 for i in range(6))


def contains(rect, x, y):
    a, b, w, h = rect
    return a <= x < a + w and b <= y < b + h


def can_stand(x, y, radius=43):
    if not (radius <= x <= WORLD_W - radius and radius <= y <= WORLD_H - radius):
        return False
    return not any(a - radius < x < a + w + radius and
                   b - radius < y < b + h + radius
                   for a, b, w, h in (*SHELVES, CHECKOUT))


@dataclass
class Actor:
    x: float = 100
    y: float = 1950
    direction: str = 'up'
    moving: bool = False
    running: bool = False
    animation: float = 0

    def move(self, dx, dy, dt, running=False):
        length = (dx * dx + dy * dy) ** 0.5
        self.moving = False
        self.running = running
        if not length:
            self.animation = 0
            return
        self.direction = ('right' if dx > 0 else 'left') if abs(dx) > abs(dy) else ('down' if dy > 0 else 'up')
        distance = (400 if running else 250) * min(dt, 0.05)
        nx, ny = self.x + dx / length * distance, self.y + dy / length * distance
        old = self.x, self.y
        in_aisle = SHELF_TOP - 43 < self.y < SHELF_TOP + SHELF_HEIGHT + 43
        entering = SHELF_TOP - 43 < ny < SHELF_TOP + SHELF_HEIGHT + 43
        if in_aisle or entering:
            center = min(AISLE_CENTERS, key=lambda value: abs(value - self.x))
            if abs(center - self.x) <= 60:
                nx = center
            elif entering:
                ny = self.y
        if can_stand(nx, self.y):
            self.x = nx
        if can_stand(self.x, ny):
            self.y = ny
        self.moving = old != (self.x, self.y)
        self.animation += dt * (12 if running else 8)

    def nearby(self):
        candidates = []
        for i, (x, y, w, h) in enumerate(SHELVES):
            if y <= self.y < y + h:
                side = -1 if self.x < x else 1
                distance = x - self.x if side == -1 else self.x - x - w
                if 0 <= distance <= 115:
                    facing = self.direction == ('right' if side == -1 else 'left')
                    candidates.append((not facing, distance, i, side))
        if not candidates:
            return None
        _, _, category, side = min(candidates)
        section = min(7, int((self.y - SHELF_TOP) / SECTION_HEIGHT))
        return category, section, side

    def align(self, category, section, side):
        x, _, w, _ = SHELVES[category]
        nx = x - 100 if side < 0 else x + w + 100
        ny = SHELF_TOP + (section + 0.5) * SECTION_HEIGHT
        if not can_stand(nx, ny):
            return False
        self.x, self.y = nx, ny
        self.direction = 'right' if side < 0 else 'left'
        return True


def camera(actor, width, height):
    return (max(0, min(WORLD_W - width, actor.x - width / 2)),
            max(0, min(WORLD_H - height, actor.y - height / 2)))
