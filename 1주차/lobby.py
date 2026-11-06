"""개별 PNG를 조합하는 로비와 스테이지·엔딩 미리보기 화면."""
import json
import os
from pathlib import Path

import pico2d

from settings import (
    WIDTH, HEIGHT, LOBBY_ASSET_DIR, LOBBY_BACKGROUND, LOBBY_PANEL,
    LOBBY_STAGE, LOBBY_LOCKED, LOBBY_ACCOUNT, LOBBY_MUTED,
)
from ui import NAVY, BLUE, inside, rounded_box, text_width, load_ui_image


STAGE_ONE = (32, 132, 211, 220)
STAGE_TWO = (255, 132, 211, 220)
PLAY = (250, 40, 300, 48)
HEADER_MARKET = (16, 493, 548, 103)
ACCOUNT_PANEL = (576, 498, 208, 94)
LOGOUT = (588, 509, 100, 28)
QUIT = (697, 509, 74, 28)
PREVIEW = (594, 60, 176, 26)
RETURN = (270, 142, 260, 48)


class LobbyUI:
    def __init__(self, session, development_mode=False):
        self.session = session
        self.development_mode = development_mode
        self.message = ""
        self.images = {}
        self.bounds = json.loads((LOBBY_ASSET_DIR / "bounds.json").read_text(encoding="utf-8"))
        for name in self.bounds:
            self.images[name] = load_ui_image(LOBBY_ASSET_DIR / (name + ".png"))
        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        self.fonts = {
            size: pico2d.load_font(str(fonts / ("malgunbd.ttf" if size >= 18 else "malgun.ttf")), size)
            for size in (12, 13, 14, 15, 16, 18, 20, 22, 24, 28)
        }

    def art(self, name, rect, stretch=False, silhouette=False, tint=None):
        image = self.images[name]
        left, top, right, bottom = self.bounds[name]
        sw, sh = right - left, bottom - top
        x, y, width, height = rect
        palette = {
            "panel_flat": LOBBY_PANEL,
            "stage_card_flat": LOBBY_STAGE,
            "stage_locked_flat": LOBBY_LOCKED,
        }
        color = (0, 0, 0) if silhouette else tint or palette.get(name, (255, 255, 255))
        pico2d.SDL_SetTextureColorMod(image.texture, *color)
        if silhouette:
            image.opacify(0.23)
        try:
            if stretch and name == "panel_flat":
                # 9분할로 넓고 얇은 패널에서도 테두리 두께를 유지한다.
                source_x = (left, left + 32, right - 32, right)
                source_y = (top, top + 32, bottom - 32, bottom)
                target_x = (x, x + 12, x + width - 12, x + width)
                target_y = (y + height, y + height - 12, y + 12, y)
                for row in range(3):
                    for column in range(3):
                        cw = source_x[column + 1] - source_x[column]
                        ch = source_y[row + 1] - source_y[row]
                        dw = target_x[column + 1] - target_x[column]
                        dh = target_y[row] - target_y[row + 1]
                        image.clip_draw(source_x[column], image.h - source_y[row + 1], cw, ch,
                                        target_x[column] + dw / 2, target_y[row + 1] + dh / 2,
                                        round(dw), round(dh))
                return
            if not stretch:
                ratio = min(width / sw, height / sh)
                width, height = sw * ratio, sh * ratio
            image.clip_draw(left, image.h - bottom, sw, sh,
                            x + rect[2] / 2, y + rect[3] / 2, round(width), round(height))
        finally:
            # 공유 텍스처의 색과 투명도가 다음 에셋에 남지 않도록 복구한다.
            pico2d.SDL_SetTextureColorMod(image.texture, 255, 255, 255)
            image.opacify(1.0)

    def text(self, text, x, y, size=16, color=NAVY, center=False, max_width=None):
        font = self.fonts[size]
        if max_width:
            for candidate in sorted((s for s in self.fonts if s <= size), reverse=True):
                font = self.fonts[candidate]
                if text_width(font, text) <= max_width:
                    break
        if center:
            x -= text_width(font, text) / 2
        font.draw(x, y, text, color)

    def button(self, rect, label, mouse, primary=False, enabled=True, size=16):
        x, y, w, h = rect
        hovered = enabled and inside(*mouse, rect)
        # 작은 확대에도 클릭 판정은 원래 버튼 사각형으로 유지한다.
        amount = 2 if hovered else 0
        self.art("button_primary" if primary and enabled else "button_secondary",
                 (x - amount, y - amount, w + amount * 2, h + amount * 2), stretch=True)
        color = (255, 255, 255) if primary and enabled else NAVY if enabled else LOBBY_MUTED
        self.text(label, x + w / 2, y + h / 2 + 1, size, color, center=True)

    def click(self, x, y):
        if inside(x, y, QUIT):
            return "quit"
        if inside(x, y, LOGOUT):
            self.session.reset()
            self.message = ""
            return "title"
        if inside(x, y, STAGE_TWO):
            if not self.session.choose_stage(2):
                self.message = "1단계를 완료하면 선택할 수 있습니다."
            else:
                self.message = "2단계를 선택했습니다."
        elif inside(x, y, STAGE_ONE):
            self.session.choose_stage(1)
            self.message = "1단계 선택 완료! 게임 시작을 눌러 주세요."
        elif inside(x, y, PLAY):
            if self.session.selected_stage is None:
                self.message = "먼저 플레이할 스테이지를 선택해 주세요."
            elif self.session.selected_stage == 2 and not self.session.stage2_unlocked:
                self.message = "1단계를 완료하면 선택할 수 있습니다."
            else:
                return "stage"
        elif self.development_mode and inside(x, y, PREVIEW):
            return "ending"
        return None

    def draw(self, mouse):
        rounded_box((0, 0, WIDTH, HEIGHT), LOBBY_BACKGROUND, 0)
        self.art("market_banner", HEADER_MARKET, stretch=True)
        self.art("panel_flat", ACCOUNT_PANEL, stretch=True, tint=LOBBY_ACCOUNT)
        self.text("닉네임", 590, 577, 12, LOBBY_MUTED)
        self.text(self.session.nickname, 590, 554, 20, max_width=180)
        self.button(LOGOUT, "로그아웃", mouse, size=14)
        self.button(QUIT, "종료", mouse, size=14)

        self.art("panel_flat", (16, 423, 768, 65), stretch=True)
        self.art("coin_icon", (29, 439, 37, 36))
        self.text("공용 인수 자금", 77, 458, 20)
        self.text("0원 (임시) / 목표 미정", 265, 458, 18)
        self.art("progress_track", (535, 451, 224, 14), stretch=True)
        self.text("목표액 확정 후 진행률 표시", 647, 436, 12, LOBBY_MUTED, center=True)

        self.art("panel_flat", (16, 112, 470, 295), stretch=True)
        self.art("cart_icon", (33, 366, 32, 29))
        self.text("스테이지 선택", 76, 380, 24)
        rounded_box((34, 361, 434, 1), (129, 154, 194), 0)
        self.art("stage_card_flat", STAGE_ONE, stretch=True)
        self.art("stage_locked_flat", STAGE_TWO, stretch=True)
        self.text("STAGE 1", 137, 328, 24, center=True)
        self.text("STAGE 2", 360, 328, 24, (104, 108, 114), center=True)
        self.art("badge", (77, 291, 120, 24), stretch=True)
        self.text("도깨비 1마리", 137, 303, 16, center=True)
        self.text("도깨비 2마리", 360, 303, 16, LOBBY_MUTED, center=True)
        self.art("dokkaebi_clean", (82, 177, 110, 106))
        self.art("dokkaebi_clean", (281, 192, 95, 86), silhouette=True)
        self.art("dokkaebi_clean", (346, 192, 95, 86), silhouette=True)
        self.art("lock_icon", (327, 195, 69, 83))
        self.art("badge", (63, 145, 148, 25), stretch=True)
        selected = self.session.selected_stage == 1
        self.text("선택 완료" if selected else "선택 가능", 137, 157, 16, BLUE, center=True)
        self.text("1스테이지 완료 시 해금", 360, 157, 14, LOBBY_MUTED, center=True)
        if inside(*mouse, STAGE_ONE):
            self.text("클릭하여 선택", 137, 183, 12, BLUE, center=True)

        self.art("panel_flat", (498, 112, 286, 295), stretch=True)
        self.art("crown_icon", (515, 369, 29, 25))
        self.text("마트 인수 기여도", 550, 382, 22, max_width=218)
        self.text("누적 보수 기준", 550, 357, 13, LOBBY_MUTED)
        rounded_box((515, 344, 251, 1), (129, 154, 194), 0)
        self.art("badge", (512, 306, 258, 29), stretch=True)
        self.text("순위", 539, 321, 14, center=True)
        self.text("닉네임", 621, 321, 14, center=True)
        self.text("기여액", 729, 321, 14, center=True)
        self.text("아직 등록된 기록이 없어요", 641, 259, 16, LOBBY_MUTED, center=True)
        self.text("함께 마트를 채워 나가요!", 641, 232, 13, LOBBY_MUTED, center=True)
        rounded_box((515, 190, 251, 1), (129, 154, 194), 0)
        self.text("내 누적 기여액", 519, 157, 16)
        self.text("0원 (임시)", 704, 157, 18, BLUE, center=True)

        self.text(self.message or f"{self.session.nickname}님, 도깨비 마트에 오신 것을 환영합니다.",
                  400, 100, 13, BLUE, center=True, max_width=760)
        self.button(PLAY, "게임 시작", mouse, primary=True,
                    enabled=self.session.selected_stage is not None, size=24)
        if self.development_mode:
            self.button(PREVIEW, "엔딩 미리보기", mouse, size=13)
        self.text("기여도와 자금은 임시 표시이며, 현재는 실행 중에만 상태가 유지됩니다.",
                  400, 21, 12, LOBBY_MUTED, center=True)

    def draw_preview(self, mouse, ending=False):
        rounded_box((0, 0, WIDTH, HEIGHT), LOBBY_BACKGROUND, 0)
        self.art("panel_flat", (105, 105, 590, 415), stretch=True)
        self.art("market_banner", (135, 336, 530, 116))
        if ending:
            self.text("엔딩 미리보기 · 개발 전용", 400, 490, 16, BLUE, center=True)
            self.text("도깨비 마트 인수 완료!", 400, 300, 28, center=True)
            self.text("모두가 모은 장보기 보수로 마트를 인수했습니다.", 400, 257, 18, center=True)
            self.text("이제 우리의 마트에서 새로운 이야기가 시작됩니다.", 400, 229, 18, center=True)
        else:
            self.text("스테이지 미리보기", 400, 490, 16, BLUE, center=True)
            self.text(f"{self.session.selected_stage}단계를 선택했습니다.", 400, 300, 28, center=True)
            self.text("장보기 기능은 개발 중입니다.", 400, 257, 18, center=True)
            self.text("미리보기에서는 보상과 스테이지 해금이 발생하지 않아요.",
                      400, 229, 14, LOBBY_MUTED, center=True)
        self.button(RETURN, "로비로 돌아가기", mouse, primary=True, size=18)
        self.button(QUIT, "종료", mouse, size=14)

    def preview_click(self, x, y, ending=False):
        if inside(x, y, QUIT):
            return "quit"
        if inside(x, y, RETURN):
            if not ending:
                self.session.return_to_lobby()
            self.message = ""
            return "lobby"
        return None
