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
        self.sources, self.thumbnails = {}, {}

    def image(self, name):
        if name not in self.images:
            path = ASSETS / (name + '.png')
            self.images[name] = p.load_image(str(path))
            p.SDL_SetTextureScaleMode(self.images[name].texture, p.SDL_ScaleModeLinear)
            with Image.open(path) as im:
                if name.startswith(('icons/', 'ui/')):
                    self.sources[name] = im.convert('RGBA')
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
        if name in self.sources:
            # GPU의 한 번짜리 선형 축소 대신 실제 화면 해상도로 필터링한다.
            sx, sy = ctypes.c_float(), ctypes.c_float()
            p.SDL_RenderGetScale(renderer(), ctypes.byref(sx), ctypes.byref(sy))
            size = (max(1, round(w * sx.value)), max(1, round(h * sy.value)))
            key = name, bounds, size
            if key not in self.thumbnails:
                source = self.sources[name].crop(bounds)
                # 알파를 미리 곱해 투명 가장자리에 검은 테두리가 생기지 않게 한다.
                thumb = source.convert('RGBa').resize(size, Image.Resampling.LANCZOS).convert('RGBA')
                pixels = ctypes.create_string_buffer(thumb.tobytes())
                surface = p.SDL_CreateRGBSurfaceFrom(pixels, *size, 32, size[0] * 4,
                                                     0xFF, 0xFF00, 0xFF0000, 0xFF000000)
                texture = p.SDL_CreateTextureFromSurface(renderer(), surface)
                p.SDL_FreeSurface(surface)
                p.SDL_SetTextureBlendMode(texture, p.SDL_BLENDMODE_BLEND)
                p.SDL_SetTextureScaleMode(texture, p.SDL_ScaleModeLinear)
                self.thumbnails[key] = p.Image(texture)
            p.SDL_RenderCopy(renderer(), self.thumbnails[key].texture, None, ctypes.byref(dst))
            return
        p.SDL_RenderCopy(renderer(), image.texture, ctypes.byref(src), ctypes.byref(dst))

    def font(self, size, bold=False, regular=False):
        key = size, bold, regular
        if key not in self.fonts:
            path = ROOT.parent / 'assets/fonts/Jua-Regular.ttf'
            regular_path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/malgun.ttf'
            if regular and regular_path.exists():
                path = regular_path
            self.fonts[key] = p.load_font(str(path), size)
        return self.fonts[key]

    def text(self, value, x, y, size=18, color=INK, center=False, max_width=None, bold=False, regular=False):
        # Thin product labels are rasterized at the actual display resolution.
        # Downsampling already small strokes from the logical canvas loses detail.
        scale = 1.0
        if regular:
            sx, sy = ctypes.c_float(), ctypes.c_float()
            p.SDL_RenderGetScale(renderer(), ctypes.byref(sx), ctypes.byref(sy))
            scale = max(.01, sy.value)
        font = self.font(max(1, round(size * scale)), bold, regular)
        def width():
            w, h = ctypes.c_int(), ctypes.c_int()
            p.TTF_SizeUTF8(font.font, value.encode('utf-8'), ctypes.byref(w), ctypes.byref(h))
            return w.value / scale
        while max_width and width() > max_width and size > 11:
            size -= 1
            font = self.font(max(1, round(size * scale)), bold, regular)
        if center:
            x -= width() / 2
        if regular:
            surface = p.TTF_RenderUTF8_Blended(font.font, value.encode('utf-8'), p.SDL_Color(*color, 255))
            texture = p.SDL_CreateTextureFromSurface(renderer(), surface)
            w, h = surface.contents.w / scale, surface.contents.h / scale
            p.SDL_FreeSurface(surface)
            try:
                p.SDL_SetTextureScaleMode(texture, p.SDL_ScaleModeLinear)
                dst = p.SDL_Rect(round(x), round(y - h / 2), round(w), round(h))
                p.SDL_RenderCopy(renderer(), texture, None, ctypes.byref(dst))
            finally:
                p.SDL_DestroyTexture(texture)
            return
        font.draw(x, p.open_canvas.__globals__['canvas_height'] - y, value, color)

    def lines(self, value, x, y, width, size=16, color=INK, bold=False, regular=False):
        # 한국어 긴 상품명은 단어 경계 없이도 두 줄로 읽을 수 있게 한다.
        capacity = max(3, int(width / size))
        if len(value) <= capacity:
            self.text(value, x, y, size, color, True, width, bold, regular)
        else:
            middle = min(capacity, (len(value) + 1) // 2)
            self.text(value[:middle], x, y - size * .5, size, color, True, width, bold, regular)
            self.text(value[middle:], x, y + size * .6, size, color, True, width, bold, regular)
