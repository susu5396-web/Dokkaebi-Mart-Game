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
            alpha = sheet.getchannel('A')
            for row in range(9):
                for col in range(6):
                    left, right = round(col * sheet.width / 6), round((col + 1) * sheet.width / 6)
                    top, bottom = round(row * sheet.height / 9), round((row + 1) * sheet.height / 9)
                    cell = alpha.crop((left, top, right, bottom))
                    # 시트의 행 경계에 걸친 이전 포즈의 작은 조각을 제외한다.
                    runs, start = [], None
                    for scan_y in range(cell.height + 1):
                        occupied = scan_y < cell.height and cell.crop((0, scan_y, cell.width, scan_y + 1)).getbbox() is not None
                        if occupied and start is None:
                            start = scan_y
                        elif not occupied and start is not None:
                            runs.append((start, scan_y))
                            start = None
                    if runs:
                        lo, hi = max(runs, key=lambda pair: pair[1] - pair[0])
                        cropped = cell.crop((0, lo, cell.width, hi)).getbbox()
                        bounds = (cropped[0], cropped[1] + lo, cropped[2], cropped[3] + lo)
                    else:
                        bounds = None
                    a, b, c, d = bounds or (0, 0, right - left, bottom - top)
                    self.frames[row, col] = (left + a, top + b, c - a, d - b)

    def draw(self, actor, x, y):
        direction = {'down': 0, 'right': 1, 'left': 1, 'up': 2}[actor.direction]
        row = direction + (6 if actor.running else 3) if actor.moving else direction
        col = int(actor.animation) % 6 if actor.moving else 0
        a, b, w, h = self.frames[row, col]
        scale = 104 / max(w, h)
        src = p.SDL_Rect(a, b, w, h)
        dst = p.SDL_Rect(int(x - w * scale / 2), int(y - h * scale / 2), int(w * scale), int(h * scale))
        flip = p.SDL_FLIP_HORIZONTAL if actor.direction == 'left' else p.SDL_FLIP_NONE
        p.SDL_RenderCopyEx(renderer(), self.image.texture, ctypes.byref(src), ctypes.byref(dst), 0, None, flip)
