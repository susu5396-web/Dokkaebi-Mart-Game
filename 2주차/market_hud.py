"""요구 목록은 표시 전용이며 카트 슬롯만 버리기를 처리한다."""
from catalog import CATEGORIES, PRODUCTS
from market_art import box, VIEW_W, SCREEN_H
from market_world import SHELVES, WORLD_W, WORLD_H, contains

MAP_RECT = (VIEW_W + 12, 12, 396, 260)
LIST_RECT = (VIEW_W + 12, 280, 396, 322)
CART_RECT = (VIEW_W + 12, 610, 396, 338)


def cart_cell(index):
    x, y, w, h = CART_RECT
    col, row = index % 3, index // 3
    return x + 16 + col * 123, y + 94 + row * 108, 118, 102


def timer_color(seconds):
    return (205, 45, 46) if seconds < 60 else (40, 61, 83)


class MarketHUD:
    def __init__(self):
        self.offset = 0

    def slots(self, state):
        ids = list(state.inventory)
        self.offset = max(0, min(self.offset, max(0, ((len(ids) - 1) // 3 - 1) * 3)))
        result = []
        for index, pid in enumerate(ids[self.offset:self.offset + 6]):
            result.append((cart_cell(index), pid))
        return result

    def click(self, x, y, state):
        for rect, pid in self.slots(state):
            if contains(rect, x, y):
                state.discard(pid)
                return True
        return False

    def scroll(self, amount, x, y, state):
        if contains(CART_RECT, x, y):
            self.offset = max(0, self.offset - amount * 3)
            self.slots(state)

    def draw(self, art, state, actor):
        box((VIEW_W, 0, 420, SCREEN_H), (224, 232, 226))
        art.draw('ui/timer_panel', (16, 16, 280, 94))
        art.text(f'{int(state.remaining)} 초', 182, 66, 30, color=timer_color(state.remaining), center=True)
        # 지도에는 매대 카테고리와 플레이어만 표시한다.
        art.draw('ui/minimap_panel', MAP_RECT, trim=True, fit=False)
        art.text('마트 지도', VIEW_W + 230, 47, 24, center=True)
        mx, my, mw, mh = VIEW_W + 30, 90, 358, 154
        for i, (sx, sy, sw, sh) in enumerate(SHELVES):
            rx, ry = mx + sx / WORLD_W * mw, my + sy / WORLD_H * mh
            rw, rh = sw / WORLD_W * mw, sh / WORLD_H * mh
            box((rx, ry, rw, rh), (126, 157, 141))
            box((rx + 3, ry + 3, rw - 6, rh - 6), (188, 208, 183))
            art.text(CATEGORIES[i], rx + rw / 2, 86, 17, center=True)
            for divider in range(1, 4):
                box((rx + 3, ry + rh * divider / 4, rw - 6, 2), (155, 180, 157))
        px, py = mx + actor.x / WORLD_W * mw, my + actor.y / WORLD_H * mh
        box((px - 6, py - 6, 12, 12), (255, 255, 255))
        box((px - 4, py - 4, 8, 8), (30, 100, 221))
        art.text('파랑: 내 위치', VIEW_W + 318, 249, 15, center=True)
        art.draw('ui/shopping_list_panel', LIST_RECT, trim=True, fit=False)
        art.text('장보기 목록', VIEW_W + 230, 318, 25, center=True)
        x, y, w, h = LIST_RECT
        for index, (pid, count) in enumerate(state.required.items()):
            product = PRODUCTS[pid]
            cy = y + 95 + index * 47
            art.draw('icons/' + product.icon, (x + 20, cy - 21, 44, 42), trim=True)
            art.lines(product.name, x + 208, cy, 238, 21)
            art.text(f'{count}개', x + 357, cy, 21, center=True)
            if index < len(state.required) - 1:
                box((x + 20, cy + 24, w - 40, 1), (180, 205, 222))
        art.draw('ui/cart_inventory_panel', CART_RECT, trim=True, fit=False)
        art.text('카트 인벤토리', VIEW_W + 230, 648, 25, center=True)
        art.text('상품 클릭: 1개 버리기', VIEW_W + 210, 685, 17, center=True)
        for index in range(6):
            sx, sy, sw, sh = cart_cell(index)
            box((sx, sy, sw, sh), (159, 191, 215))
            box((sx + 2, sy + 2, sw - 4, sh - 4), (253, 249, 237))
        for (sx, sy, sw, sh), pid in self.slots(state):
            product = PRODUCTS[pid]
            art.draw('icons/' + product.icon, (sx + 22, sy + 5, 68, 58), trim=True)
            art.lines(product.name, sx + sw / 2, sy + 80, sw - 12, 17)
            box((sx + sw - 38, sy + 43, 34, 22), (66, 116, 185))
            art.text(f'x{state.inventory[pid]}', sx + sw - 21, sy + 54, 16, (255, 255, 255), True)
        if not state.inventory:
            art.text('카트가 비어 있습니다', VIEW_W + 210, 932, 17, center=True)
        if len(state.inventory) > 6:
            art.text('마우스 휠: 다른 상품 보기', VIEW_W + 210, 932, 17, center=True)
