"""시작 → 닉네임 → 로비 → 스테이지 미리보기의 공통 게임 루프."""
import ctypes
from time import perf_counter

import pico2d
from settings import (
    WIDTH, HEIGHT, BUTTON_WIDTH, BUTTON_HEIGHT, BUTTON_X, BUTTON_Y,
    HOVER_SCALE, ASSET_DIR, DEVELOPMENT_MODE,
)
from session import Session
from ui import NicknameUI, inside, FIELD, CONFIRM, BACK
from lobby import LobbyUI


def collect_events():
    # pico2d 기본 함수가 제외하는 한글 조합·확정 이벤트까지 수집한다.
    # SDL_Event는 매번 재사용되므로 프레임 단위로 처리할 때 반드시 복사한다.
    events = []
    event = pico2d.SDL_Event()
    while pico2d.SDL_PollEvent(ctypes.byref(event)):
        events.append(pico2d.SDL_Event.from_buffer_copy(event))
    return events


class Game:
    def __init__(self, development_mode=DEVELOPMENT_MODE):
        self.background = pico2d.load_image(str(ASSET_DIR / "start.png"))
        self.start_button = pico2d.load_image(str(ASSET_DIR / "start_button.png"))
        self.name_background = pico2d.load_image(str(ASSET_DIR / "name_background.png"))
        self.session = Session()
        self.nickname_ui = NicknameUI()
        self.lobby = LobbyUI(self.session, development_mode)
        self.scene = "title"
        self.pending_scene = None
        self.running = True
        self.scale = 1.0
        self.mouse = (-1, -1)
        pico2d.SDL_StopTextInput()

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
        self.nickname_ui.focus(False)
        self.scene = self.pending_scene
        self.pending_scene = None
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
            e.type == pico2d.SDL_KEYDOWN and e.key.keysym.sym == pico2d.SDLK_ESCAPE
        ) for e in events):
            self.running = False
            return
        for event in events:
            if self.pending_scene is not None or not self.running:
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
                x, y = event.button.x, HEIGHT - 1 - event.button.y
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
        mouse_x, mouse_y = ctypes.c_int(), ctypes.c_int()
        pico2d.SDL_GetMouseState(ctypes.byref(mouse_x), ctypes.byref(mouse_y))
        if pico2d.SDL_GetMouseFocus():
            self.mouse = (mouse_x.value, HEIGHT - 1 - mouse_y.value)
        else:
            self.mouse = (-1, -1)
        x, y = self.mouse
        hovered = abs(x - BUTTON_X) <= BUTTON_WIDTH / 2 and abs(y - BUTTON_Y) <= BUTTON_HEIGHT / 2
        target = HOVER_SCALE if hovered else 1.0
        self.scale += (target - self.scale) * min(1.0, dt * 16.0)

    def draw(self):
        pico2d.clear_canvas()
        if self.scene == "title":
            self.background.draw(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            self.start_button.draw(BUTTON_X, BUTTON_Y,
                                   round(BUTTON_WIDTH * self.scale), round(BUTTON_HEIGHT * self.scale))
        elif self.scene == "nickname":
            self.name_background.draw(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
            self.nickname_ui.draw(*self.mouse)
        elif self.scene == "lobby":
            self.lobby.draw(self.mouse)
        else:
            self.lobby.draw_preview(self.mouse, self.scene == "ending")


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
