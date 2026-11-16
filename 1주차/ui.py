"""공통 그리기 함수와 닉네임 입력 UI."""
import ctypes
import math
import os
from pathlib import Path
from time import perf_counter

import pico2d
from settings import WIDTH, HEIGHT, FONT_PATH

NAVY = (25, 48, 88)
BLUE = (66, 115, 180)
MUTED = (105, 118, 138)
FIELD = (122, 215, 555, 76)
CONFIRM = (353, 108, 273, 70)
BACK = (171, 108, 165, 70)


def load_ui_image(path):
    """고해상도 UI를 축소할 때 픽셀 경계가 튀지 않도록 선형 보간한다."""
    image = pico2d.load_image(str(path))
    pico2d.SDL_SetTextureScaleMode(image.texture, pico2d.SDL_ScaleModeLinear)
    return image


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
        self.title_font = pico2d.load_font(str(FONT_PATH), 42)
        self.font = pico2d.load_font(str(FONT_PATH), 28)
        self.small = pico2d.load_font(str(FONT_PATH), 17)
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
            rect = pico2d.SDL_Rect(FIELD[0], HEIGHT - FIELD[1] - FIELD[3], FIELD[2], FIELD[3])
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
        centered(self.title_font, '닉네임을 입력해주세요', 393)
        centered(self.small, '마트에서 사용할 이름을 알려주세요', 335, MUTED)
        display = self.value + self.composition
        self.font.draw(153, 254, display or '닉네임', NAVY if display else MUTED)
        end_x = 153 + text_width(self.font, display)
        if self.composition:
            start_x = 153 + text_width(self.font, self.value)
            rounded_box((start_x, 235, max(2, end_x - start_x), 2), BLUE, 0)
        if self.focused and perf_counter() % 1 < .5:
            rounded_box((end_x + 3, 237, 2, 30), BLUE, 0)
        self.small.draw(131, 199, '한글 / 영문 / 숫자 / 최대 12자', MUTED)
        self.small.draw(620, 199, f'{len(self.value)} / 12', MUTED)
        if self.error:
            centered(self.small, self.error, 185, (177, 65, 56))
        for rect, label, color in ((BACK, '뒤로', NAVY), (CONFIRM, '확인', (255, 255, 255))):
            left, bottom, width, height = rect
            self.font.draw(left + (width - text_width(self.font, label)) / 2,
                           bottom + height / 2, label, BLUE if inside(x, y, rect) else color)

