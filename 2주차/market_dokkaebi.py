"""매대와 계산대를 우회하는 도깨비 추적. 월드 좌표만 사용한다."""
from dataclasses import dataclass, field
from functools import lru_cache
from heapq import heappop, heappush
from math import hypot, cos, sin, atan2, tau

from market_world import (SHELVES, CHECKOUT, can_stand, DOKKAEBI_DEN,
                          DOKKAEBI_SPEED, DOKKAEBI_FLEE_SPEED, dokkaebi_dens)

RADIUS = 43
PLAYER_RADIUS = 63
ENEMY_RADIUS = 57
FOLLOW_DISTANCE = PLAYER_RADIUS + ENEMY_RADIUS
ATTACK_RANGE = 180
STEAL_RANGE = FOLLOW_DISTANCE + 12
ESCAPE_DELAY = 5.0
RESPAWN_DELAY = 5.0
VANISH_DURATION = .6
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


def movement_clear(start, end, blockers, radius):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_squared = dx * dx + dy * dy
    for other, other_radius in blockers:
        if getattr(other, 'phase', 'active') != 'active':
            continue
        t = max(0, min(1, ((other.x - start[0]) * dx + (other.y - start[1]) * dy) / length_squared)) if length_squared else 0
        distance = hypot(start[0] + t * dx - other.x, start[1] + t * dy - other.y)
        if distance < radius + other_radius - 1e-6:
            return False
    return True


@dataclass
class Dokkaebi:
    x: float
    y: float
    direction: str = 'down'
    moving: bool = False
    animation: float = 0
    path: list = field(default_factory=list)
    repath_in: float = 0

    phase: str = 'active'
    respawn_in: float = 0
    stolen_pid: str | None = None
    escape_in: float = 0
    home_den: tuple = DOKKAEBI_DEN

    def banish(self):
        if self.phase != 'active':
            return False
        self.stolen_pid = None
        self.escape_in = 0
        self.phase = 'vanishing'
        self.respawn_in = RESPAWN_DELAY
        self.moving = False
        self.path.clear()
        return True

    def approach_route(self, target, blockers):
        best, best_length = [], float('inf')
        start = self.x, self.y
        for index in range(16):
            angle = tau * index / 16
            goal = target.x + (FOLLOW_DISTANCE + 1) * cos(angle), target.y + (FOLLOW_DISTANCE + 1) * sin(angle)
            if not clear_path(goal, (target.x, target.y)):
                continue
            candidate = route(start, goal)
            previous, length = start, 0
            for point in candidate:
                if not movement_clear(previous, point, blockers, ENEMY_RADIUS):
                    break
                length += hypot(point[0] - previous[0], point[1] - previous[1])
                previous = point
            else:
                if candidate and length < best_length:
                    best, best_length = candidate, length
        return best

    def flee_route(self, target, blockers):
        start = self.x, self.y
        dx, dy = self.x - target.x, self.y - target.y
        if hypot(dx, dy) < 1e-6:
            dx, dy = {'right': (1, 0), 'left': (-1, 0), 'down': (0, 1), 'up': (0, -1)}[self.direction]
        length = hypot(dx, dy)
        away = dx / length, dy / length
        angle = atan2(away[1], away[0])
        best, best_score = [], float('-inf')
        for distance in (360, 540, 720):
            for offset in (0, -tau / 12, tau / 12, -tau / 6, tau / 6, -tau / 4, tau / 4):
                goal = (self.x + cos(angle + offset) * distance,
                        self.y + sin(angle + offset) * distance)
                if not can_stand(*goal, RADIUS):
                    continue
                candidate = route(start, goal)
                previous, path_length = start, 0
                for point in candidate:
                    if not movement_clear(previous, point, blockers, ENEMY_RADIUS):
                        break
                    path_length += hypot(point[0] - previous[0], point[1] - previous[1])
                    previous = point
                else:
                    progress = (goal[0] - self.x) * away[0] + (goal[1] - self.y) * away[1]
                    score = progress - path_length * .12
                    if candidate and score > best_score:
                        best, best_score = candidate, score
        return best

    def update(self, dt, target, others=()):
        elapsed = max(0, dt)
        fleeing = self.phase == 'active' and self.stolen_pid is not None
        if fleeing:
            self.escape_in = max(0, self.escape_in - elapsed)
            if self.escape_in <= 1e-6:
                self.banish()
                return
        if self.phase != 'active':
            self.respawn_in = max(0, self.respawn_in - elapsed)
            if self.respawn_in <= RESPAWN_DELAY - VANISH_DURATION:
                self.phase = 'hidden'
            if self.respawn_in <= 1e-6:
                # 배정된 굴 입구가 막혀 있으면 다른 굴로 옮기지 않고 기다린다.
                blockers = [(target, PLAYER_RADIUS)] + [(other, ENEMY_RADIUS) for other in others if other is not self]
                x, y, w, h = self.home_den
                point = x + w / 2, y + h / 2
                if can_stand(*point) and movement_clear(point, point, blockers, ENEMY_RADIUS):
                    self.x, self.y = point
                    self.phase = 'active'
                    self.repath_in = 0
                    self.animation = 0
            return
        dt = max(0, min(dt, .05))
        self.moving = False
        start, goal = (self.x, self.y), (target.x, target.y)
        direct = clear_path(start, goal)
        if not fleeing and direct and hypot(self.x - target.x, self.y - target.y) <= FOLLOW_DISTANCE + 1e-6:
            self.path.clear()
            self.repath_in = 0
            return
        self.repath_in -= dt
        if fleeing:
            if self.repath_in <= 0 or not self.path:
                blockers = [(target, PLAYER_RADIUS)] + [(other, ENEMY_RADIUS) for other in others if other is not self]
                self.path = self.flee_route(target, blockers)
                self.repath_in = REPATH_INTERVAL
        elif direct:
            self.path = [goal]
        elif self.repath_in <= 0 or not self.path:
            self.path = route(start, goal)
            self.repath_in = REPATH_INTERVAL
        budget = (DOKKAEBI_FLEE_SPEED if fleeing else DOKKAEBI_SPEED) * dt
        while self.path and budget > 0:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            distance = hypot(dx, dy)
            if distance < 1e-6:
                self.path.pop(0)
                continue
            step = min(distance, budget)
            if not fleeing and direct and len(self.path) == 1:
                step = min(step, max(0, distance - FOLLOW_DISTANCE))
            if step <= 1e-6:
                break
            nx, ny = self.x + dx / distance * step, self.y + dy / distance * step
            if not clear_path((self.x, self.y), (nx, ny)):
                self.path.clear()
                self.repath_in = 0
                break
            blockers = [(target, PLAYER_RADIUS)] + [(other, ENEMY_RADIUS) for other in others if other is not self]
            if not movement_clear((self.x, self.y), (nx, ny), blockers, ENEMY_RADIUS):
                self.path = self.flee_route(target, blockers) if fleeing else self.approach_route(target, blockers)
                self.repath_in = REPATH_INTERVAL
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
    return [Dokkaebi(x + w / 2, y + h / 2, home_den=(x, y, w, h))
            for x, y, w, h in dokkaebi_dens(stage)]


class DokkaebiSprite:
    def __init__(self):
        import pico2d as p
        from market_art import ROOT
        self.image = p.load_image(str(ROOT.parent / '1주차/dokkaebi_sheet1.png'))
        p.SDL_SetTextureScaleMode(self.image.texture, p.SDL_ScaleModeLinear)
        self.vanish_image = p.load_image(str(ROOT.parent / '1주차/dokkaebi_sheet.png'))
        p.SDL_SetTextureScaleMode(self.vanish_image.texture, p.SDL_ScaleModeLinear)

    def draw(self, actor, x, y):
        import ctypes
        import pico2d as p
        from market_art import renderer
        if actor.phase == 'hidden':
            return
        direction = {'down': 0, 'right': 1, 'left': 1, 'up': 2}[actor.direction]
        row = direction + (9 if actor.stolen_pid is not None else 3 if actor.moving else 0)
        column = int(actor.animation) % (6 if actor.moving or actor.stolen_pid is not None else 4)
        texture = self.image.texture
        if actor.phase == 'vanishing':
            row = 12
            column = min(5, int((RESPAWN_DELAY - actor.respawn_in) / VANISH_DURATION * 6))
            texture = self.vanish_image.texture
        src = p.SDL_Rect(column * 128, row * 128, 128, 128)
        dst = p.SDL_Rect(round(x - 72), round(y - 72), 144, 144)
        flip = p.SDL_FLIP_HORIZONTAL if actor.direction == 'left' else p.SDL_FLIP_NONE
        p.SDL_RenderCopyEx(renderer(), texture, ctypes.byref(src), ctypes.byref(dst), 0, None, flip)
