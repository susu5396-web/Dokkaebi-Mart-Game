"""도깨비 마트 시작 화면: 배경과 마우스 오버 버튼."""

import ctypes
from pathlib import Path
from time import perf_counter

import pico2d


WIDTH, HEIGHT = 800,600
BUTTON_WIDTH, BUTTON_HEIGHT = 300, 100
BUTTON_MARGIN = 24
BUTTON_X = WIDTH - BUTTON_MARGIN - BUTTON_WIDTH / 2
BUTTON_Y = BUTTON_MARGIN + BUTTON_HEIGHT / 2
HOVER_SCALE = 1.08
ASSET_DIR = Path(__file__).resolve().parent


def main():
    pico2d.open_canvas(WIDTH, HEIGHT)
    try:
        background = pico2d.load_image(str(ASSET_DIR / "start.png"))
        start_button = pico2d.load_image(str(ASSET_DIR / "start_button.png"))
        name_background = pico2d.load_image(str(ASSET_DIR / "name_background.png"))
        scene = "title"
        mouse_x, mouse_y = ctypes.c_int(), ctypes.c_int()
        scale = 1.0
        previous_time = perf_counter()
        running = True

        while running:
            now = perf_counter()
            dt = min(now - previous_time, 0.05)
            previous_time = now

            for event in pico2d.get_events():
                if event.type == pico2d.SDL_QUIT:
                    running = False
                elif event.type == pico2d.SDL_KEYDOWN and event.key == pico2d.SDLK_ESCAPE:
                    running = False
                elif scene == "title" and event.type == pico2d.SDL_MOUSEBUTTONDOWN:
                    if event.button == pico2d.SDL_BUTTON_LEFT and (
                        abs(event.x - BUTTON_X) <= BUTTON_WIDTH / 2
                        and abs(HEIGHT - 1 - event.y - BUTTON_Y) <= BUTTON_HEIGHT / 2
                    ):
                        scene = "nickname"

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
            pico2d.update_canvas()
            pico2d.delay(0.01)
    finally:
        pico2d.close_canvas()


if __name__ == "__main__":
    main()
