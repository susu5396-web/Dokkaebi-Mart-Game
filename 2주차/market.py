"""장보기 장면의 입력 및 수명 관리."""
import pico2d as p
from catalog import PRODUCTS
from market_state import MarketState
from market_world import Actor, contains
from market_art import Art, VIEW_W
from market_player import PlayerSprite
from market_hud import MarketHUD
from market_view import draw_world, draw_shelf, product_slots
from market_result import draw_result, RESULT_BUTTON
from session import Session

UP = (p.SDLK_w, p.SDLK_UP)
DOWN = (p.SDLK_s, p.SDLK_DOWN)
LEFT = (p.SDLK_a, p.SDLK_LEFT)
RIGHT = (p.SDLK_d, p.SDLK_RIGHT)


class Market:
    def __init__(self, session=None):
        self.session = session if session is not None else Session()
        self.art, self.sprite = Art(), PlayerSprite()
        self.reset()

    def reset(self):
        self.state, self.actor, self.hud = MarketState(), Actor(), MarketHUD()
        self.keys = set()
        self.shelf = None
        self.message, self.message_time = '', 0
        self.stage = self.session.selected_stage or 1
        self.reward = 0
        self.checkout_inside = False
        self.differences = []
        self.inspection_time = 0

    def preload(self):
        # 원본 PNG와 축소 텍스처를 첫 게임 입장 전에 캐시에 준비한다.
        self.draw()
        draw_shelf(self.art, self.state, 0, 0, '')
        width = product_slots()[0][2]
        for icon in {product.icon for product in PRODUCTS.values()}:
            for w, h in ((55, 53), (85, 73), (width - 24, 270)):
                self.art.draw('icons/' + icon, (0, 0, w, h), trim=True)

    def inspect_cart(self):
        if self.shelf or not self.actor.at_checkout() or self.state.outcome is not None:
            return
        self.differences = self.state.checkout()
        self.inspection_time = 6 if self.differences else 0
        if self.state.outcome == 'success':
            self.reward = self.session.complete_stage(self.stage)
            self.keys.clear()
            self.actor.moving = False

    def result_destination(self):
        return 'ending' if self.state.outcome == 'success' and self.session.acquired else 'lobby'

    def handle(self, event):
        if self.state.outcome is not None:
            if event.type == p.SDL_KEYDOWN and not event.key.repeat and event.key.keysym.sym in (
                    p.SDLK_RETURN, p.SDLK_KP_ENTER, p.SDLK_ESCAPE):
                return self.result_destination()
            if (event.type == p.SDL_MOUSEBUTTONDOWN and event.button.button == p.SDL_BUTTON_LEFT
                    and contains(RESULT_BUTTON, event.button.x, event.button.y)):
                return self.result_destination()
            return None

        if event.type == p.SDL_WINDOWEVENT and event.window.event == p.SDL_WINDOWEVENT_FOCUS_LOST:
            self.keys.clear()
        elif event.type == p.SDL_KEYUP:
            self.keys.discard(event.key.keysym.sym)
        elif event.type == p.SDL_KEYDOWN:
            key = event.key.keysym.sym
            previous = set(self.keys)
            self.keys.add(key)
            if event.key.repeat:
                return None
            if key == p.SDLK_ESCAPE:
                if self.shelf:
                    self.shelf = None
                    self.keys.clear()
                else:
                    return 'lobby'
            elif key == p.SDLK_e:
                if self.shelf:
                    self.shelf = None
                elif self.actor.at_checkout():
                    self.inspect_cart()
                else:
                    nearby = self.actor.nearby()
                    if nearby and self.actor.align(*nearby):
                        self.shelf = nearby
                self.keys.clear()
                self.actor.moving = False
            elif self.shelf and key in (*UP, *DOWN):
                direction_keys = UP if key in UP else DOWN
                if any(k in previous for k in direction_keys):
                    return None
                category, section, side = self.shelf
                target = section + (-1 if key in UP else 1)
                if 0 <= target < 8 and self.actor.align(category, target, side):
                    self.shelf = category, target, side
        elif event.type == p.SDL_MOUSEBUTTONDOWN and event.button.button == p.SDL_BUTTON_LEFT:
            x, y = event.button.x, event.button.y
            if x >= VIEW_W:
                self.hud.click(x, y, self.state)
            elif self.shelf:
                category, section, _ = self.shelf
                for index, rect in enumerate(product_slots()):
                    if contains(rect, x, y):
                        pid = self.state.layout[category][section][index]
                        self.state.add(pid)
                        self.message = PRODUCTS[pid].name + ' 1개를 담았습니다.'
                        self.message_time = 2
                        break
            else:
                self.hud.click(x, y, self.state)
        elif event.type == p.SDL_MOUSEWHEEL:
            import ctypes
            x, y = ctypes.c_int(), ctypes.c_int()
            p.SDL_GetMouseState(ctypes.byref(x), ctypes.byref(y))
            from market_art import renderer
            lx, ly = ctypes.c_float(), ctypes.c_float()
            p.SDL_RenderWindowToLogical(renderer(), x.value, y.value, ctypes.byref(lx), ctypes.byref(ly))
            self.hud.scroll(event.wheel.y, lx.value, ly.value, self.state)
        return None

    def update(self, dt):
        self.state.update(dt)
        if self.state.outcome is not None:
            self.keys.clear()
            self.actor.moving = False
            return
        self.inspection_time = max(0, self.inspection_time - dt)
        self.message_time -= dt
        if self.message_time <= 0:
            self.message = ''
        if not self.shelf:
            down = lambda keys: any(key in self.keys for key in keys)
            self.actor.move(int(down(RIGHT)) - int(down(LEFT)),
                            int(down(DOWN)) - int(down(UP)), dt,
                            down((p.SDLK_LSHIFT, p.SDLK_RSHIFT)))
            inside = self.actor.at_checkout()
            if inside and not self.checkout_inside:
                self.inspect_cart()
            self.checkout_inside = inside

    def draw(self):
        if self.shelf:
            draw_shelf(self.art, self.state, *self.shelf[:2], self.message)
        else:
            draw_world(self.art, self.actor, self.sprite)
        self.hud.draw(self.art, self.state, self.actor)
        draw_result(self.art, self)
