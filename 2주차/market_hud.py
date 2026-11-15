"""요구 목록은 표시 전용이며 카트 슬롯만 버리기를 처리한다."""
from catalog import CATEGORIES, PRODUCTS
from market_art import box
from market_world import SHELVES, WORLD_W, WORLD_H, contains

LIST_RECT = (920, 345, 300, 375)
CART_RECT = (930, 724, 280, 224)


def timer_color(seconds):
    return (205, 45, 46) if seconds < 60 else (40, 61, 83)


class MarketHUD:
    def __init__(self):
        self.offset = 0

    def slots(self, state):
        ids = list(state.inventory)
        self.offset = max(0, min(self.offset, max(0, ((len(ids) - 1) // 3 - 1) * 3)))
        x, y, w, h = CART_RECT
        result = []
        for index, pid in enumerate(ids[self.offset:self.offset + 6]):
            col, row = index % 3, index // 3
            result.append(((x + w * (.07 + col * .297), y + h * (.32 + row * .30),
                            w * .275, h * .265), pid))
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
        box((860, 0, 420, 960), (224, 232, 226))
        art.text('도깨비 마트', 1070, 24, 25, center=True)
        art.draw('ui/timer_panel', (16, 16, 280, 94))
        art.text(f'{int(state.remaining)} 초', 182, 66, 30, color=timer_color(state.remaining), center=True)
        # 지도에는 매대 카테고리와 플레이어만 표시한다.
        art.draw('ui/minimap_panel', (920, 40, 300, 300))
        art.text('마트 지도', 1085, 83, 19, center=True)
        mx, my, mw, mh = 945, 111, 250, 176
        for i, (sx, sy, sw, sh) in enumerate(SHELVES):
            rx, ry = mx + sx / WORLD_W * mw, my + sy / WORLD_H * mh
            box((rx, ry, max(8, sw / WORLD_W * mw), sh / WORLD_H * mh), (155, 177, 152))
            # 좁은 지도에서 이름을 세로로 쌓아 겹침을 피한다.
            for j, char in enumerate(CATEGORIES[i]):
                art.text(char, rx + 5, ry + 22 + j * 19, 16, center=True)
        px, py = mx + actor.x / WORLD_W * mw, my + actor.y / WORLD_H * mh
        box((px - 4, py - 4, 8, 8), (30, 100, 221))
        art.text('파랑: 플레이어', 1070, 318, 15, center=True)
        art.draw('ui/shopping_list_panel', LIST_RECT)
        x, y, w, h = LIST_RECT
        for index, (pid, count) in enumerate(state.required.items()):
            product = PRODUCTS[pid]
            cy = y + h * (.365 + index * .103)
            art.draw('icons/' + product.icon, (x + 32, cy - 17, 34, 34), trim=True)
            art.lines(product.name, x + 152, cy, 152, 15)
            art.text(f'{count}개', x + 255, cy, 16, center=True)
        art.draw('ui/cart_inventory_panel', CART_RECT)
        for (sx, sy, sw, sh), pid in self.slots(state):
            product = PRODUCTS[pid]
            art.draw('icons/' + product.icon, (sx + 17, sy + 2, sw - 34, 31), trim=True)
            art.lines(product.name, sx + sw / 2, sy + sh - 13, sw - 7, 11)
            box((sx + sw - 28, sy + 20, 25, 17), (66, 116, 185))
            art.text(f'x{state.inventory[pid]}', sx + sw - 16, sy + 28, 11, (255, 255, 255), True)
        if not state.inventory:
            art.text('카트가 비어 있습니다', 1070, 839, 14, center=True)
        if len(state.inventory) > 6:
            art.text('카트 위에서 휠: 다른 상품 보기', 1070, 952, 12, center=True)
