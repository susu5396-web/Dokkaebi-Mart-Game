"""매대와 계산대를 우회하는 도깨비 추적. 월드 좌표만 사용한다."""
from dataclasses import dataclass, field
from functools import lru_cache
from heapq import heappop, heappush
from math import hypot

from market_world import SHELVES, CHECKOUT, can_stand, DOKKAEBI_DEN, DOKKAEBI_SPEED

RADIUS = 43
FOLLOW_DISTANCE = 65
REPATH_INTERVAL = .25


def clear_path(start, end):
    """선분과 반지름만큼 확장한 장애물의 교차 여부를 검사한다."""
    if not can_stand(*start, RADIUS) or not can_stand(*end, RADIUS):
        return False
    dx, dy = end[0] - start[0], end[1] - start[1]
    for x, y, w, h in (*SHELVES, CHECKOUT):
        low, high = 0.0, 1.0
        for origin, delta, minimum, maximum in (
                (start[0], dx, x - RADIUS + 1e-6, x + w + RADIUS - 1e-6),
                (start[1], dy, y - RADIUS + 1e-6, y + h + RADIUS - 1e-6)):
            if abs(delta) < 1e-9:
                if not minimum <= origin <= maximum:
                    low, high = 1, 0
                    break
            else:
                a, b = (minimum - origin) / delta, (maximum - origin) / delta
                low, high = max(low, min(a, b)), min(high, max(a, b))
        if low <= high:
            return False
    return True


@lru_cache(maxsize=1)
def navigation_graph():
    margin = RADIUS + 8
    nodes = []
    for x, y, w, h in (*SHELVES, CHECKOUT):
        for point in ((x - margin, y - margin), (x + w + margin, y - margin),
                      (x - margin, y + h + margin), (x + w + margin, y + h + margin)):
            if can_stand(*point, RADIUS):
                nodes.append(point)
    edges = [[] for _ in nodes]
    for i, start in enumerate(nodes):
        for j in range(i + 1, len(nodes)):
            if clear_path(start, nodes[j]):
                distance = hypot(start[0] - nodes[j][0], start[1] - nodes[j][1])
                edges[i].append((j, distance))
                edges[j].append((i, distance))
    return nodes, edges


def route(start, target):
    if clear_path(start, target):
        return [target]
    fixed_nodes, fixed_edges = navigation_graph()
    nodes = [*fixed_nodes, start, target]
    edges = [list(neighbors) for neighbors in fixed_edges] + [[], []]
    first, last = len(nodes) - 2, len(nodes) - 1
    for endpoint in (first, last):
        for index, point in enumerate(fixed_nodes):
            if clear_path(nodes[endpoint], point):
                distance = hypot(nodes[endpoint][0] - point[0], nodes[endpoint][1] - point[1])
                edges[endpoint].append((index, distance))
                edges[index].append((endpoint, distance))
    distances, previous, queue = {first: 0}, {}, [(0, first)]
    while queue:
        cost, current = heappop(queue)
        if cost != distances[current]:
            continue
        if current == last:
            path = []
            while current != first:
                path.append(nodes[current])
                current = previous[current]
            return path[::-1]
        for neighbor, distance in edges[current]:
            candidate = cost + distance
            if candidate < distances.get(neighbor, float('inf')):
                distances[neighbor] = candidate
                previous[neighbor] = current
                heappush(queue, (candidate, neighbor))
    return []


@dataclass
class Dokkaebi:
    x: float
    y: float
    direction: str = 'down'
    moving: bool = False
    animation: float = 0
    path: list = field(default_factory=list)
    repath_in: float = 0

    def update(self, dt, target):
        dt = max(0, min(dt, .05))
        self.moving = False
        start, goal = (self.x, self.y), (target.x, target.y)
        direct = clear_path(start, goal)
        if direct and hypot(self.x - target.x, self.y - target.y) <= FOLLOW_DISTANCE + 1e-6:
            self.path.clear()
            self.repath_in = 0
            return
        self.repath_in -= dt
        if direct:
            self.path = [goal]
        elif self.repath_in <= 0 or not self.path:
            self.path = route(start, goal)
            self.repath_in = REPATH_INTERVAL
        budget = DOKKAEBI_SPEED * dt
        while self.path and budget > 0:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            distance = hypot(dx, dy)
            if distance < 1e-6:
                self.path.pop(0)
                continue
            step = min(distance, budget)
            if direct and len(self.path) == 1:
                step = min(step, max(0, distance - FOLLOW_DISTANCE))
            if step <= 1e-6:
                break
            nx, ny = self.x + dx / distance * step, self.y + dy / distance * step
            if not clear_path((self.x, self.y), (nx, ny)):
                self.path.clear()
                self.repath_in = 0
                break
            self.x, self.y = nx, ny
            self.direction = ('right' if dx > 0 else 'left') if abs(dx) > abs(dy) else ('down' if dy > 0 else 'up')
            self.moving = True
            budget -= step
            if step >= distance - 1e-6:
                self.path.pop(0)
        if self.moving:
            self.animation += dt * 10


def spawn_dokkaebi(stage):
    x, y, w, h = DOKKAEBI_DEN
    center_x, center_y = x + w / 2, y + h / 2
    return [Dokkaebi(center_x, center_y)] if stage == 1 else [
        Dokkaebi(center_x - 35, center_y), Dokkaebi(center_x + 35, center_y + 25)]


class DokkaebiSprite:
    def __init__(self):
        import pico2d as p
        from market_art import ROOT
        self.image = p.load_image(str(ROOT.parent / '1주차/dokkaebi_sheet1.png'))
        p.SDL_SetTextureScaleMode(self.image.texture, p.SDL_ScaleModeLinear)

    def draw(self, actor, x, y):
        import ctypes
        import pico2d as p
        from market_art import renderer
        direction = {'down': 0, 'right': 1, 'left': 1, 'up': 2}[actor.direction]
        row = direction + (3 if actor.moving else 0)
        column = int(actor.animation) % (6 if actor.moving else 4)
        src = p.SDL_Rect(column * 128, row * 128, 128, 128)
        dst = p.SDL_Rect(round(x - 72), round(y - 72), 144, 144)
        flip = p.SDL_FLIP_HORIZONTAL if actor.direction == 'left' else p.SDL_FLIP_NONE
        p.SDL_RenderCopyEx(renderer(), self.image.texture, ctypes.byref(src), ctypes.byref(dst), 0, None, flip)
