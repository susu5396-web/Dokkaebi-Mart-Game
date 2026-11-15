"""6열 9행 플레이어·카트 시트의 대기/걷기/달리기 재생."""
import ctypes
import pico2d as p
from PIL import Image
from market_art import ROOT, renderer


class PlayerSprite:
    def __init__(self):
        path = ROOT.parent / '1주차' / 'player_sheet.png'
        self.image = p.load_image(str(path))
        p.SDL_SetTextureScaleMode(self.image.texture, p.SDL_ScaleModeLinear)
        self.frames = {}
        with Image.open(path) as sheet:
            alpha = sheet.getchannel('A').point(lambda value: 255 if value > 128 else 0)
            for col in range(6):
                left, right = round(col * sheet.width / 6), round((col + 1) * sheet.width / 6)
                strip = alpha.crop((left, 0, right, sheet.height))
                occupied = [y for y in range(sheet.height)
                            if sum(strip.crop((0, y, strip.width, y + 1)).getdata()) > 6 * 255]
                runs = []
                for y in occupied:
                    if not runs or y - runs[-1][1] > 4:
                        runs.append([y, y + 1])
                    else:
                        runs[-1][1] = y + 1
                runs = [run for run in runs if run[1] - run[0] > 60]
                if len(runs) != 9:
                    raise ValueError(f'플레이어 시트 {col}열의 포즈 수가 9개가 아닙니다.')
                for row, (top, bottom) in enumerate(runs):
                    top, bottom = max(0, top - 2), min(sheet.height, bottom + 2)
                    a, b, c, d = strip.crop((0, top, strip.width, bottom)).getbbox()
                    self.frames[row, col] = (left + a, top + b, c - a, d - b)
        self.scale = 104 / max(max(frame[2:]) for frame in self.frames.values())

    def draw(self, actor, x, y):
        direction = {'down': 0, 'right': 1, 'left': 1, 'up': 2}[actor.direction]
        row = direction + (6 if actor.running else 3) if actor.moving else direction
        col = int(actor.animation) % 6 if actor.moving else 0
        a, b, w, h = self.frames[row, col]
        scale = self.scale
        src = p.SDL_Rect(a, b, w, h)
        dst = p.SDL_Rect(int(x - w * scale / 2), int(y - h * scale / 2), int(w * scale), int(h * scale))
        flip = p.SDL_FLIP_HORIZONTAL if actor.direction == 'left' else p.SDL_FLIP_NONE
        p.SDL_RenderCopyEx(renderer(), self.image.texture, ctypes.byref(src), ctypes.byref(dst), 0, None, flip)
