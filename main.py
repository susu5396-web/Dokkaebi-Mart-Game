"""시작 → 닉네임 → 로비 → 스테이지 미리보기의 공통 게임 루프."""
import ctypes
import sys
from time import perf_counter
from pathlib import Path

import pico2d

sys.path.insert(0, str(Path(__file__).resolve().parent / "1주차"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "2주차"))

from settings import (
    WIDTH, HEIGHT, BUTTON_WIDTH, BUTTON_HEIGHT, BUTTON_X, BUTTON_Y,
    HOVER_SCALE, ASSET_DIR, START_ASSET_DIR, DEVELOPMENT_MODE,
)
from session import Session
from ui import NicknameUI, inside, load_ui_image, FIELD, CONFIRM, BACK
from lobby import LobbyUI
from market import Market
from market_art import SCREEN_W, SCREEN_H

WINDOW_W, WINDOW_H = 950, 622
MENU_X, MENU_Y = (WINDOW_W - WIDTH) // 2, (WINDOW_H - HEIGHT) // 2
FADE_OUT, FADE_IN = .12, .16


def collect_events():
    # pico2d 기본 함수가 제외하는 한글 조합·확정 이벤트까지 수집한다.
    # SDL_Event는 매번 재사용되므로 프레임 단위로 처리할 때 반드시 복사한다.
    events = []
    event = pico2d.SDL_Event()
    while pico2d.SDL_PollEvent(ctypes.byref(event)):
        events.append(pico2d.SDL_Event.from_buffer_copy(event))
    return events


class Game:
    def __init__(self, development_mode=DEVELOPMENT_MODE, animate_transitions=True):
        self.background = load_ui_image(START_ASSET_DIR / "start-wide.png")
        self.start_button = load_ui_image(START_ASSET_DIR / "start_button.png")
        self.name_background = load_ui_image(Path(__file__).resolve().parent / '2주차/assets/ui/nickname_background.png')
        self.session = Session()
        self.nickname_ui = NicknameUI()
        self.lobby = LobbyUI(self.session, development_mode)
        self.scene = "title"
        self.pending_scene = None
        self.running = True
        self.scale = 1.0
        self.mouse = (-1, -1)
        self.market = None
        self.animate_transitions = animate_transitions
        self.fade_phase = None
        self.fade_time = 0.0
        canvas = pico2d.open_canvas.__globals__
        pico2d.SDL_SetWindowSize(canvas['window'], WINDOW_W, WINDOW_H)
        pico2d.SDL_SetWindowPosition(canvas['window'], pico2d.SDL_WINDOWPOS_CENTERED, pico2d.SDL_WINDOWPOS_CENTERED)
        self.configure_renderer()
        pico2d.SDL_StopTextInput()
        # 첫 화면을 먼저 보여주고 리소스를 준비해 게임 입장 때의 로딩을 없앤다.
        self.draw()
        pico2d.update_canvas()
        self.market = Market(self.session)
        self.configure_renderer(stage=True)
        self.market.preload()
        self.configure_renderer()

    def configure_renderer(self, stage=None):
        renderer = pico2d.open_canvas.__globals__['renderer']
        pico2d.SDL_RenderSetViewport(renderer, None)
        is_stage = self.scene == 'stage' if stage is None else stage
        if is_stage:
            pico2d.SDL_RenderSetLogicalSize(renderer, SCREEN_W, SCREEN_H)
        else:
            pico2d.SDL_RenderSetLogicalSize(renderer, 0, 0)
            pico2d.SDL_RenderSetScale(renderer, 1, 1)
            if self.scene not in ("title", "lobby", "ending"):
                viewport = pico2d.SDL_Rect(MENU_X, MENU_Y, WIDTH, HEIGHT)
                pico2d.SDL_RenderSetViewport(renderer, ctypes.byref(viewport))

    def menu_position(self, x, y):
        if self.scene in ("lobby", "ending"):
            return x * WIDTH / WINDOW_W, (WINDOW_H - 1 - y) * HEIGHT / WINDOW_H
        return x - MENU_X, HEIGHT - 1 - (y - MENU_Y)

    def request_scene(self, scene):
        if scene == "quit":
            self.running = False
        elif scene:
            self.pending_scene = scene

    def confirm_nickname(self):
        self.nickname_ui.submit()
        if self.nickname_ui.saved_name:
            self.session.nickname = self.nickname_ui.saved_name
            self.request_scene("lobby")

    def apply_transition(self):
        if self.pending_scene is None:
            return
        if self.fade_phase is not None:
            return
        if self.animate_transitions and 'stage' in (self.scene, self.pending_scene):
            self.fade_phase = 'out'
            self.fade_time = 0.0
            if self.market:
                self.market.keys.clear()
            return
        self.commit_transition()

    def commit_transition(self):
        self.nickname_ui.focus(False)
        if self.scene == 'stage' and self.pending_scene == 'lobby':
            self.session.selected_stage = None
        self.scene = self.pending_scene
        self.pending_scene = None
        if self.scene == 'stage':
            if self.market is None:
                self.market = Market(self.session)
            else:
                self.market.reset()
        self.configure_renderer()
        if self.scene == "nickname":
            self.nickname_ui.value = ""
            self.nickname_ui.saved_name = ""
            self.nickname_ui.error = ""
            self.nickname_ui.focus(True)
        elif self.scene == "title":
            self.session.reset()
            self.nickname_ui.value = ""
            self.nickname_ui.saved_name = ""
            self.nickname_ui.error = ""
            self.lobby.message = ""

    def handle_events(self, events):
        # 화면 전환보다 종료를 우선하고, 전환 프레임의 잔여 입력은 소비한다.
        if any(e.type == pico2d.SDL_QUIT or (
            self.scene != 'stage' and e.type == pico2d.SDL_KEYDOWN and e.key.keysym.sym == pico2d.SDLK_ESCAPE
        ) for e in events):
            self.running = False
            return
        for event in events:
            if self.pending_scene is not None or self.fade_phase is not None or not self.running:
                continue
            if self.scene == 'stage':
                self.request_scene(self.market.handle(event))
                continue
            if event.type == pico2d.SDL_KEYDOWN:
                if event.key.repeat:
                    continue
                key = event.key.keysym.sym
                if self.scene == "nickname":
                    if key == pico2d.SDLK_BACKSPACE and self.nickname_ui.focused:
                        if not self.nickname_ui.composition:
                            self.nickname_ui.value = self.nickname_ui.value[:-1]
                            self.nickname_ui.error = ""
                    elif key in (pico2d.SDLK_RETURN, pico2d.SDLK_KP_ENTER):
                        self.confirm_nickname()
                    elif key == pico2d.SDLK_TAB:
                        self.nickname_ui.focus(True)
            elif event.type == pico2d.SDL_TEXTINPUT:
                if self.scene == "nickname" and self.nickname_ui.focused:
                    self.nickname_ui.append(bytes(event.text.text).decode("utf-8"))
            elif event.type == pico2d.SDL_TEXTEDITING:
                if self.scene == "nickname" and self.nickname_ui.focused:
                    self.nickname_ui.composition = bytes(event.edit.text).decode("utf-8")
                    self.nickname_ui.error = ""
            elif event.type == pico2d.SDL_MOUSEBUTTONDOWN and event.button.button == pico2d.SDL_BUTTON_LEFT:
                x, y = self.menu_position(event.button.x, event.button.y)
                if self.scene == "title":
                    if abs(x - BUTTON_X) <= BUTTON_WIDTH / 2 and abs(y - BUTTON_Y) <= BUTTON_HEIGHT / 2:
                        self.request_scene("nickname")
                elif self.scene == "nickname":
                    if inside(x, y, BACK):
                        self.request_scene("title")
                    elif inside(x, y, CONFIRM):
                        self.confirm_nickname()
                    else:
                        self.nickname_ui.focus(inside(x, y, FIELD))
                elif self.scene == "lobby":
                    self.request_scene(self.lobby.click(x, y))
                elif self.scene in ("stage", "ending"):
                    self.request_scene(self.lobby.preview_click(x, y, self.scene == "ending"))
        if self.running:
            self.apply_transition()

    def update(self, dt):
        if self.fade_phase is not None:
            self.fade_time += dt
            if self.fade_phase == 'out' and self.fade_time >= FADE_OUT:
                # 검은 프레임을 한 번 표시하고 창 변경 없이 장면만 바꾼다.
                self.fade_phase = 'switch'
            elif self.fade_phase == 'switch':
                self.commit_transition()
                self.fade_phase = 'in'
                self.fade_time = 0.0
            elif self.fade_phase == 'in' and self.fade_time >= FADE_IN:
                self.fade_phase = None
            return
        if self.scene == 'stage':
            self.market.update(dt)
            return
        mouse_x, mouse_y = ctypes.c_int(), ctypes.c_int()
        pico2d.SDL_GetMouseState(ctypes.byref(mouse_x), ctypes.byref(mouse_y))
        if pico2d.SDL_GetMouseFocus():
            self.mouse = self.menu_position(mouse_x.value, mouse_y.value)
        else:
            self.mouse = (-1, -1)
        x, y = self.mouse
        hovered = abs(x - BUTTON_X) <= BUTTON_WIDTH / 2 and abs(y - BUTTON_Y) <= BUTTON_HEIGHT / 2
        target = HOVER_SCALE if hovered else 1.0
        self.scale += (target - self.scale) * min(1.0, dt * 16.0)

    def draw(self):
        renderer = pico2d.open_canvas.__globals__['renderer']
        # 전체 버퍼를 먼저 채워 뷰포트 바깥에 이전 화면의 선이 남지 않게 한다.
        pico2d.SDL_SetRenderDrawColor(renderer, 239, 242, 225, 255)
        pico2d.SDL_RenderClear(renderer)
        if self.scene == "title":
            self.background.draw(WINDOW_W / 2, HEIGHT - WINDOW_H / 2, WINDOW_W, WINDOW_H)
            self.start_button.draw(BUTTON_X + MENU_X, BUTTON_Y - MENU_Y,
                                   round(BUTTON_WIDTH * self.scale), round(BUTTON_HEIGHT * self.scale))
        elif self.scene == "nickname":
            self.name_background.draw(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            self.nickname_ui.draw(*self.mouse)
        elif self.scene == "lobby":
            self.lobby.draw(self.mouse)
        elif self.scene == 'stage':
            self.market.draw()
        else:
            self.lobby.draw_preview(self.mouse, self.scene == "ending")
        if self.fade_phase is not None:
            opacity = (min(1.0, self.fade_time / FADE_OUT) if self.fade_phase == 'out'
                       else max(0.0, 1.0 - self.fade_time / FADE_IN) if self.fade_phase == 'in' else 1.0)
            renderer = pico2d.open_canvas.__globals__['renderer']
            pico2d.SDL_RenderSetLogicalSize(renderer, 0, 0)
            pico2d.SDL_RenderSetScale(renderer, 1, 1)
            pico2d.SDL_RenderSetViewport(renderer, None)
            pico2d.SDL_SetRenderDrawBlendMode(renderer, pico2d.SDL_BLENDMODE_BLEND)
            pico2d.SDL_SetRenderDrawColor(renderer, 0, 0, 0, round(255 * opacity))
            pico2d.SDL_RenderFillRect(renderer, None)
            pico2d.SDL_SetRenderDrawBlendMode(renderer, pico2d.SDL_BLENDMODE_NONE)
            self.configure_renderer()


def main():
    pico2d.open_canvas(WIDTH, HEIGHT)
    try:
        game = Game()
        previous_time = perf_counter()
        while game.running:
            now = perf_counter()
            dt = min(now - previous_time, 0.05)
            previous_time = now
            game.handle_events(collect_events())
            if not game.running:
                break
            game.update(dt)
            game.draw()
            pico2d.update_canvas()
            pico2d.delay(0.01)
    finally:
        pico2d.SDL_StopTextInput()
        pico2d.close_canvas()


if __name__ == "__main__":
    main()
