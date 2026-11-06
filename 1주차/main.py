"""도깨비 마트 시작 화면과 닉네임 입력 화면."""
import ctypes
from time import perf_counter

import pico2d
from settings import (
    WIDTH, HEIGHT, BUTTON_WIDTH, BUTTON_HEIGHT, BUTTON_X, BUTTON_Y,
    HOVER_SCALE, ASSET_DIR,
)
from ui import NicknameUI, inside, FIELD, CONFIRM, BACK

def collect_events():
    # pico2d.get_events drops SDL_TEXTINPUT/SDL_TEXTEDITING, so keep them here.
    event = pico2d.SDL_Event()
    while pico2d.SDL_PollEvent(ctypes.byref(event)):
        yield event


def main():
    pico2d.open_canvas(WIDTH, HEIGHT)
    try:
        background = pico2d.load_image(str(ASSET_DIR / "start.png"))
        start_button = pico2d.load_image(str(ASSET_DIR / "start_button.png"))
        name_background = pico2d.load_image(str(ASSET_DIR / "name_background.png"))
        scene = "title"
        nickname_ui = NicknameUI()
        pico2d.SDL_StopTextInput()
        mouse_x, mouse_y = ctypes.c_int(), ctypes.c_int()
        scale = 1.0
        previous_time = perf_counter()
        running = True

        while running:
            now = perf_counter()
            dt = min(now - previous_time, 0.05)
            previous_time = now

            for event in collect_events():
                if event.type == pico2d.SDL_QUIT:
                    running = False
                elif event.type == pico2d.SDL_KEYDOWN:
                    key = event.key.keysym.sym
                    if key == pico2d.SDLK_ESCAPE:
                        running = False
                    elif scene == "nickname" and not nickname_ui.saved_name:
                        if key == pico2d.SDLK_BACKSPACE and nickname_ui.focused:
                            if not nickname_ui.composition:
                                nickname_ui.value = nickname_ui.value[:-1]
                                nickname_ui.error = ""
                        elif key in (pico2d.SDLK_RETURN, pico2d.SDLK_KP_ENTER):
                            nickname_ui.submit()
                        elif key == pico2d.SDLK_TAB:
                            nickname_ui.focus(True)
                elif event.type == pico2d.SDL_TEXTINPUT:
                    if scene == "nickname" and nickname_ui.focused:
                        nickname_ui.append(bytes(event.text.text).decode("utf-8"))
                elif event.type == pico2d.SDL_TEXTEDITING:
                    if scene == "nickname" and nickname_ui.focused:
                        nickname_ui.composition = bytes(event.edit.text).decode("utf-8")
                elif event.type == pico2d.SDL_MOUSEBUTTONDOWN and event.button.button == pico2d.SDL_BUTTON_LEFT:
                    x, y = event.button.x, HEIGHT - 1 - event.button.y
                    if scene == "title":
                        if abs(x - BUTTON_X) <= BUTTON_WIDTH / 2 and abs(y - BUTTON_Y) <= BUTTON_HEIGHT / 2:
                            scene = "nickname"
                            nickname_ui.focus(True)
                    elif inside(x, y, BACK):
                        scene = "title"
                        nickname_ui.focus(False)
                        nickname_ui.saved_name = ""
                    elif inside(x, y, CONFIRM):
                        if nickname_ui.saved_name:
                            nickname_ui.saved_name = ""
                            nickname_ui.focus(True)
                        else:
                            nickname_ui.submit()
                    elif not nickname_ui.saved_name:
                        nickname_ui.focus(inside(x, y, FIELD))

            if not running:
                break

            pico2d.SDL_GetMouseState(ctypes.byref(mouse_x), ctypes.byref(mouse_y))
            # SDL은 왼쪽 위, pico2d는 왼쪽 아래가 좌표 원점이다.
            x, y = mouse_x.value, HEIGHT - 1 - mouse_y.value
            # 판정 영역은 기본 크기로 고정해 확대 경계에서 깜빡이지 않게 한다.
            hovered = bool(pico2d.SDL_GetMouseFocus()) and (
                abs(x - BUTTON_X) <= BUTTON_WIDTH / 2
                and abs(y - BUTTON_Y) <= BUTTON_HEIGHT / 2
            )
            target_scale = HOVER_SCALE if hovered else 1.0
            scale += (target_scale - scale) * min(1.0, dt * 16.0)

            pico2d.clear_canvas()
            if scene == "title":
                background.draw(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
                start_button.draw(
                    BUTTON_X, BUTTON_Y,
                    round(BUTTON_WIDTH * scale), round(BUTTON_HEIGHT * scale),
                )
            else:
                name_background.draw(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
                nickname_ui.draw(x, y)
            pico2d.update_canvas()
            pico2d.delay(0.01)
    finally:
        pico2d.SDL_StopTextInput()
        pico2d.close_canvas()


if __name__ == "__main__":
    main()
