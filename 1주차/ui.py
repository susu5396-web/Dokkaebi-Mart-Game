"""공통 그리기 함수와 닉네임 입력 UI."""
import ctypes
import math
import os
from pathlib import Path
from time import perf_counter

import pico2d
from settings import WIDTH, HEIGHT

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
        centered(self.small, "닉네임 · 최대 12자", 463, BLUE)
        if self.saved_name:
            centered(self.title_font, "도깨비 마트에 오신 걸 환영해요!", 398)
            centered(self.font, self.saved_name + "님, 반가워요!", 345)
            centered(self.font, "닉네임이 준비되었어요.", 310)
            centered(self.small, "이 이름으로 장보기 소동을 함께해요!", 283, MUTED)
            label = "로비 입장"
        else:
            centered(self.title_font, "원하시는 이름을 적어 주세요.", 408)
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
            label = "완료"
        rounded_box((270, 169, 260, 52), NAVY, 14)
        rounded_box(CONFIRM, (85, 139, 203) if inside(x, y, CONFIRM) else BLUE, 14)
        centered(self.font, label, 200, (255, 255, 255))
        centered(self.small, "← 시작 화면으로", 142, BLUE if inside(x, y, BACK) else MUTED)

