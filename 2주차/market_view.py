"""월드와 매대의 시각 표현. 입력과 수량 변경은 장면에서 처리한다."""
from catalog import CATEGORIES
from market_art import VIEW_W, VIEW_H, box, clip
from market_world import SHELVES, CHECKOUT, camera


def draw_world(art, actor, sprite):
    cx, cy = camera(actor, VIEW_W, VIEW_H)
    clip((0, 0, VIEW_W, VIEW_H))
    tile = 320
    for y in range(int(cy // tile) * tile, int(cy + VIEW_H) + tile, tile):
        for x in range(int(cx // tile) * tile, int(cx + VIEW_W) + tile, tile):
            art.draw('environment/topview_floor', (x - cx, y - cy, tile, tile))
    for category, (x, y, w, h) in enumerate(SHELVES):
        # 세 개의 긴 모듈을 연결해 이동 가능한 8구간 매대를 표현한다.
        for part in range(3):
            art.draw('environment/topview_shelf', (x - cx, y + part * h / 3 - cy, w, h / 3), trim=True, fit=False)
        for label_y in (y - 26, y + h + 28):
            box((x - cx - 8, label_y - cy - 19, w + 16, 38), (253, 245, 225))
            art.text(CATEGORIES[category], x + w / 2 - cx, label_y - cy, 24, center=True)
    x, y, w, h = CHECKOUT
    art.draw('environment/checkout', (x - cx, y - cy, w, h), trim=True)
    art.text('계산대 · 출발 지점', x + w / 2 - cx, y + h + 24 - cy, 18, center=True)
    sprite.draw(actor, actor.x - cx, actor.y - cy)
    nearby = actor.nearby()
    if nearby:
        box((210, VIEW_H - 66, 500, 42), (253, 245, 225))
        art.text(f'E  {CATEGORIES[nearby[0]]} 매대 살펴보기', VIEW_W / 2, VIEW_H - 45, 23, center=True)
    clip()
    box((0, VIEW_H, VIEW_W, 70), (238, 230, 208))
    art.text('WASD / 방향키 이동   Shift 달리기   E 매대 보기', 24, VIEW_H + 23, 18)
    art.text('장보기 목록을 보고 상품을 찾아보세요.  Esc 로비로 돌아가기', 24, VIEW_H + 49, 16)
