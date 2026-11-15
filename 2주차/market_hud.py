"""요구 목록은 표시 전용이며 카트 슬롯만 버리기를 처리한다."""
from catalog import CATEGORIES, PRODUCTS
from market_art import box
from market_world import SHELVES, WORLD_W, WORLD_H, contains

LIST_RECT = (984, 339, 230, 287)
CART_RECT = (931, 656, 338, 270)


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
        box((920, 0, 360, 960), (224, 232, 226))
        art.text('도깨비 마트', 1100, 24, 25, center=True)
        art.draw('ui/timer_panel', (942, 43, 316, 83))
        art.text(f'{int(state.remaining)} 초', 1125, 86, 30, center=True)
        # 지도에는 매대 카테고리와 플레이어만 표시한다.
        art.draw('ui/minimap_panel', (1004, 130, 192, 192))
        art.text('마트 지도', 1109, 156, 16, center=True)
        mx, my, mw, mh = 1019, 176, 161, 112
        for i, (sx, sy, sw, sh) in enumerate(SHELVES):
            rx, ry = mx + sx / WORLD_W * mw, my + sy / WORLD_H * mh
            box((rx, ry, max(8, sw / WORLD_W * mw), sh / WORLD_H * mh), (155, 177, 152))
            # 좁은 지도에서 이름을 세로로 쌓아 겹침을 피한다.
            for j, char in enumerate(CATEGORIES[i]):
                art.text(char, rx + 5, ry + 14 + j * 14, 12, center=True)
        px, py = mx + actor.x / WORLD_W * mw, my + actor.y / WORLD_H * mh
        box((px - 4, py - 4, 8, 8), (30, 100, 221))
        art.text('파랑: 플레이어', 1100, 303, 12, center=True)
        art.draw('ui/shopping_list_panel', LIST_RECT)
        x, y, w, h = LIST_RECT
        for index, (pid, count) in enumerate(state.required.items()):
            product = PRODUCTS[pid]
            cy = y + h * (.365 + index * .103)
            art.draw('icons/' + product.icon, (x + 26, cy - 13, 27, 27), trim=True)
            art.lines(product.name, x + 117, cy, 116, 12)
            art.text(f'{count}개', x + 193, cy, 13, center=True)
        art.draw('ui/cart_inventory_panel', CART_RECT)
        for (sx, sy, sw, sh), pid in self.slots(state):
            product = PRODUCTS[pid]
            art.draw('icons/' + product.icon, (sx + 18, sy + 3, sw - 36, 42), trim=True)
            art.lines(product.name, sx + sw / 2, sy + sh - 17, sw - 7, 12)
            box((sx + sw - 28, sy + 28, 25, 19), (66, 116, 185))
            art.text(f'x{state.inventory[pid]}', sx + sw - 16, sy + 37, 12, (255, 255, 255), True)
        if not state.inventory:
            art.text('카트가 비어 있습니다', 1100, 806, 16, center=True)
        if len(state.inventory) > 6:
            art.text('카트 위에서 휠: 다른 상품 보기', 1100, 944, 13, center=True)
