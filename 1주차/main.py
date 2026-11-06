"""도깨비 마트 시작 화면: 배경과 마우스 오버 버튼."""

import ctypes
import math
import os
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



NAVY = (25, 48, 88)
BLUE = (66, 115, 180)
MUTED = (105, 118, 138)
FIELD = (190, 278, 420, 62)
CONFIRM = (270, 174, 260, 52)
BACK = (334, 126, 132, 32)


def inside(x, y, rect):
    left, bottom, width, height = rect
    return left <= x <= left + width and bottom <= y <= bottom + height


def rounded_box(rect, color, radius=14):
    # SDL draws from the top left; UI coordinates use pico2d's bottom left.
    renderer = pico2d.open_canvas.__globals__["renderer"]
    left, bottom, width, height = map(int, rect)
    pico2d.SDL_SetRenderDrawColor(renderer, *color, 255)
    for row in range(height):
        edge = max(radius - row - 0.5, row - (height - radius) + 0.5, 0)
        inset = int(radius - math.sqrt(max(0, radius * radius - edge * edge)))
        y = HEIGHT - 1 - bottom - row
        pico2d.SDL_RenderDrawLine(renderer, left + inset, y, left + width - inset - 1, y)


def text_width(font, text):
    width, height = ctypes.c_int(), ctypes.c_int()
    pico2d.TTF_SizeUTF8(font.font, text.encode("utf-8"), ctypes.byref(width), ctypes.byref(height))
    return width.value


def centered(font, text, y, color=NAVY):
    font.draw((WIDTH - text_width(font, text)) / 2, y, text, color)


class NicknameUI:
    def __init__(self):
        font_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        self.title_font = pico2d.load_font(str(font_dir / "malgunbd.ttf"), 30)
        self.font = pico2d.load_font(str(font_dir / "malgun.ttf"), 20)
        self.small = pico2d.load_font(str(font_dir / "malgun.ttf"), 14)
        self.value = ""
        self.composition = ""
        self.error = ""
        self.saved_name = ""
        self.focused = False

    def focus(self, enabled):
        self.focused = enabled
        self.composition = ""
        if enabled:
            pico2d.SDL_StartTextInput()
            rect = pico2d.SDL_Rect(FIELD[0], HEIGHT - FIELD[1], FIELD[2], 24)
            pico2d.SDL_SetTextInputRect(ctypes.byref(rect))
        else:
            pico2d.SDL_StopTextInput()

    def append(self, text):
        available = 12 - len(self.value)
        self.value += text[:available]
        self.composition = ""
        self.error = "닉네임은 최대 12자까지 입력할 수 있어요." if len(text) > available else ""

    def submit(self):
        if self.composition:
            return
        name = self.value.strip()
        if not name:
            self.error = "닉네임을 입력해 주세요."
            self.focus(True)
            return
        self.value = self.saved_name = name
        self.error = ""
        self.focus(False)

    def draw(self, x, y):
        rounded_box((139, 99, 530, 390), (215, 210, 192), 24)
        rounded_box((135, 105, 530, 390), NAVY, 24)
        rounded_box((138, 108, 524, 384), (255, 252, 243), 22)
        rounded_box((325, 450, 150, 26), (228, 237, 246), 12)
        centered(self.small, "도깨비 마트 · 입장 카드", 463, BLUE)
        if self.saved_name:
            centered(self.title_font, "반가워요, " + self.saved_name + "님!", 386)
            centered(self.font, "닉네임이 준비되었어요.", 320)
            centered(self.small, "이 이름으로 장보기 소동을 함께해요!", 283, MUTED)
            label = "닉네임 수정"
        else:
            centered(self.title_font, "어떤 이름으로 불러드릴까요?", 408)
            centered(self.small, "도깨비 마트에서 사용할 닉네임을 적어 주세요.", 372, MUTED)
            border = BLUE if self.focused else (174, 187, 201)
            rounded_box(FIELD, border, 12)
            rounded_box((192, 280, 416, 58), (255, 255, 252), 10)
            display = self.value + self.composition
            if display:
                self.font.draw(207, 309, display, NAVY)
            else:
                self.font.draw(207, 309, "닉네임 입력", (154, 163, 174))
            end_x = 207 + text_width(self.font, display)
            if self.composition:
                start_x = 207 + text_width(self.font, self.value)
                rounded_box((start_x, 292, max(2, end_x - start_x), 2), BLUE, 0)
            if self.focused and perf_counter() % 1 < 0.5:
                rounded_box((end_x + 2, 295, 2, 26), BLUE, 0)
            self.small.draw(194, 259, "한글 · 영문 · 숫자 / 최대 12자", MUTED)
            self.small.draw(562, 259, f"{len(self.value)} / 12", MUTED)
            if self.error:
                centered(self.small, self.error, 235, (177, 65, 56))
            label = "이 이름으로 할게요"
        rounded_box((270, 169, 260, 52), NAVY, 14)
        rounded_box(CONFIRM, (85, 139, 203) if inside(x, y, CONFIRM) else BLUE, 14)
        centered(self.font, label, 200, (255, 255, 255))
        centered(self.small, "← 시작 화면으로", 142, BLUE if inside(x, y, BACK) else MUTED)


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
