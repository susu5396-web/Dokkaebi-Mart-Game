"""장보기 전용 좌상단 좌표 렌더링과 에셋 캐시."""
import ctypes
import os
from pathlib import Path
import pico2d as p
from PIL import Image

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
SCREEN_W, SCREEN_H = 1467, 960
VIEW_W, VIEW_H = 1047, 890
INK = (40, 61, 83)


def renderer():
    return p.open_canvas.__globals__['renderer']


def box(rect, color):
    p.SDL_SetRenderDrawColor(renderer(), *color, 255)
    r = p.SDL_Rect(*map(int, rect))
    p.SDL_RenderFillRect(renderer(), ctypes.byref(r))


def clip(rect=None):
    r = p.SDL_Rect(*map(int, rect)) if rect else None
    p.SDL_RenderSetClipRect(renderer(), ctypes.byref(r) if r else None)


class Art:
    def __init__(self):
        self.images, self.bounds, self.fonts = {}, {}, {}

    def image(self, name):
        if name not in self.images:
            path = ASSETS / (name + '.png')
            self.images[name] = p.load_image(str(path))
            p.SDL_SetTextureScaleMode(self.images[name].texture, p.SDL_ScaleModeLinear)
            with Image.open(path) as im:
                # 생성 PNG의 거의 투명한 외곽 점 때문에 매대 크기가 줄지 않게 한다.
                self.bounds[name] = (im.getchannel('A').point(lambda alpha: 255 if alpha > 128 else 0).getbbox()
                                     if im.mode == 'RGBA' else (0, 0, im.width, im.height))
        return self.images[name]

    def draw(self, name, rect, trim=False, fit=True):
        image = self.image(name)
        bounds = self.bounds[name] if trim else (0, 0, image.w, image.h)
        a, b, c, d = bounds
        x, y, w, h = rect
        if fit:
            scale = min(w / (c - a), h / (d - b))
            nw, nh = (c - a) * scale, (d - b) * scale
            x, y, w, h = x + (w - nw) / 2, y + (h - nh) / 2, nw, nh
        src = p.SDL_Rect(a, b, c - a, d - b)
        dst = p.SDL_Rect(*map(int, (x, y, w, h)))
        p.SDL_RenderCopy(renderer(), image.texture, ctypes.byref(src), ctypes.byref(dst))

    def font(self, size):
        if size not in self.fonts:
            path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'malgun.ttf'
            self.fonts[size] = p.load_font(str(path), size)
        return self.fonts[size]

    def text(self, value, x, y, size=18, color=INK, center=False, max_width=None):
        font = self.font(size)
        def width():
            w, h = ctypes.c_int(), ctypes.c_int()
            p.TTF_SizeUTF8(font.font, value.encode('utf-8'), ctypes.byref(w), ctypes.byref(h))
            return w.value
        while max_width and width() > max_width and size > 11:
            size -= 1
            font = self.font(size)
        if center:
            x -= width() / 2
        # pico2d 글꼴 좌표는 기존 캔버스 높이를 기준으로 변환된다.
        font.draw(x, p.open_canvas.__globals__['canvas_height'] - y, value, color)

    def lines(self, value, x, y, width, size=16, color=INK):
        # 한국어 긴 상품명은 단어 경계 없이도 두 줄로 읽을 수 있게 한다.
        capacity = max(3, int(width / size))
        if len(value) <= capacity:
            self.text(value, x, y, size, color, True, width)
        else:
            middle = min(capacity, (len(value) + 1) // 2)
            self.text(value[:middle], x, y - size * .5, size, color, True, width)
            self.text(value[middle:], x, y + size * .6, size, color, True, width)
