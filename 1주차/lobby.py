"""개별 PNG를 조합하는 로비와 스테이지·엔딩 미리보기 화면."""
import json
import pico2d

from settings import (
    WIDTH, HEIGHT, LOBBY_ASSET_DIR, LOBBY_BACKGROUND, LOBBY_PANEL,
    LOBBY_STAGE, LOBBY_LOCKED, LOBBY_ACCOUNT, LOBBY_MUTED, FONT_PATH,
)
from records import format_time
from ui import NAVY, BLUE, inside, rounded_box as base_rounded_box, text_width, load_ui_image


# Draw at native window resolution while retaining layout coordinates.
SCALE_X, SCALE_Y = 950 / WIDTH, 622 / HEIGHT


def screen_rect(rect):
    x, y, w, h = rect
    return x * SCALE_X, HEIGHT - 622 + y * SCALE_Y, w * SCALE_X, h * SCALE_Y


def rounded_box(rect, color, radius=14):
    base_rounded_box(screen_rect(rect), color, radius)


STAGE_ONE = (32, 122, 211, 230)
STAGE_TWO = (255, 122, 211, 230)
PLAY = (250, 40, 300, 48)
HEADER_MARKET = (16, 493, 548, 103)
ACCOUNT_PANEL = (576, 498, 208, 94)
LOGOUT = (588, 509, 100, 28)
QUIT = (697, 509, 74, 28)
PREVIEW = (594, 60, 176, 26)
RETURN = (270, 142, 260, 48)
RANK_TABS = {1: (506, 374, 130, 36), 2: (640, 374, 130, 36)}
RANK_PREVIOUS = (516, 164, 48, 24)
RANK_NEXT = (718, 164, 48, 24)
RANK_PAGE_SIZE = 4


class LobbyUI:
    def __init__(self, session, development_mode=False):
        self.session = session
        self.development_mode = development_mode
        self.message = ""
        self.ranking_stage = 1
        self.ranking_page = 0
        self.images = {}
        self.bounds = json.loads((LOBBY_ASSET_DIR / "bounds.json").read_text(encoding="utf-8"))
        for name in self.bounds:
            self.images[name] = load_ui_image(LOBBY_ASSET_DIR / (name + ".png"))
        self.fonts = {
            size: pico2d.load_font(str(FONT_PATH), size)
            for size in range(12, 37)
        }

    def art(self, name, rect, stretch=False, silhouette=False, tint=None):
        rect = screen_rect(rect)
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
        x, y = x * SCALE_X, HEIGHT - 622 + y * SCALE_Y
        size = min(36, round(size * 1.22))
        max_width = max_width * SCALE_X if max_width else None
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
        for stage, rect in RANK_TABS.items():
            if inside(x, y, rect):
                self.ranking_stage = stage
                self.ranking_page = 0
                return None
        page_count = max(1, (len(self.session.records.ranking(self.ranking_stage)) + RANK_PAGE_SIZE - 1) // RANK_PAGE_SIZE)
        if inside(x, y, RANK_PREVIOUS):
            self.ranking_page = max(0, self.ranking_page - 1)
            return None
        if inside(x, y, RANK_NEXT):
            self.ranking_page = min(page_count - 1, self.ranking_page + 1)
            return None
        if inside(x, y, QUIT):
            return "quit"
        if inside(x, y, LOGOUT):
            self.session.reset()
            self.ranking_stage = 1
            self.ranking_page = 0
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

        self.art("panel_flat", (16, 112, 470, 295), stretch=True)
        self.art("cart_icon", (33, 366, 32, 29))
        self.text("스테이지 선택", 76, 380, 24)
        rounded_box((34, 361, 434, 1), (129, 154, 194), 0)
        self.art("stage_card_flat", STAGE_ONE, stretch=True)
        self.art("stage_card_flat" if self.session.stage2_unlocked else "stage_locked_flat", STAGE_TWO, stretch=True)
        self.text("STAGE 1", 137, 328, 24, center=True)
        self.text("STAGE 2", 360, 328, 24, (104, 108, 114), center=True)
        self.art("badge", (77, 291, 120, 24), stretch=True)
        self.text("도깨비 1마리", 137, 303, 16, center=True)
        self.text("도깨비 2마리", 360, 303, 16, LOBBY_MUTED, center=True)
        self.art("dokkaebi_clean", (72, 171, 130, 126))
        self.art("dokkaebi_clean", (281, 192, 95, 86), silhouette=not self.session.stage2_unlocked)
        self.art("dokkaebi_clean", (346, 192, 95, 86), silhouette=not self.session.stage2_unlocked)
        if not self.session.stage2_unlocked:
            self.art("lock_icon", (320, 188, 83, 100))
        self.art("badge", (63, 145, 148, 25), stretch=True)
        selected = self.session.selected_stage == 1
        self.text("선택 완료" if selected else "선택 가능", 137, 157, 16, BLUE, center=True)
        stage_two_label = ('선택 완료' if self.session.selected_stage == 2 else '선택 가능') if self.session.stage2_unlocked else '1스테이지 완료 시 해금'
        self.text(stage_two_label, 360, 157, 14, BLUE if self.session.stage2_unlocked else LOBBY_MUTED, center=True)

        self.draw_ranking(mouse)

        self.text(self.message or f"{self.session.nickname}님, 도깨비 마트에 오신 것을 환영합니다.",
                  400, 100, 13, BLUE, center=True, max_width=760)
        self.button(PLAY, "게임 시작", mouse, primary=True,
                    enabled=self.session.selected_stage is not None, size=24)
        if self.development_mode:
            self.button(PREVIEW, "엔딩 미리보기", mouse, size=13)
        self.text(self.session.records.error or "최고 기록은 이 PC에 저장됩니다. 로그아웃하거나 게임을 종료해도 유지됩니다.",
                  400, 21, 12, LOBBY_MUTED, center=True, max_width=760)

    def draw_ranking(self, mouse):
        border = (129, 154, 194)
        # 뒤쪽 인덱스를 먼저 그리고 선택한 탭을 앞쪽 종이에 연결한다.
        for stage, rect in RANK_TABS.items():
            rounded_box(rect, border, 8)
            x, y, w, h = rect
            rounded_box((x + 2, y + 2, w - 4, h - 4),
                        LOBBY_PANEL if stage == self.ranking_stage else LOBBY_STAGE, 7)
        rounded_box((498, 112, 286, 266), border, 10)
        rounded_box((500, 114, 282, 262), LOBBY_PANEL, 8)
        x, y, w, h = RANK_TABS[self.ranking_stage]
        rounded_box((x + 2, 371, w - 4, 10), LOBBY_PANEL, 0)
        for stage, rect in RANK_TABS.items():
            self.text(f'스테이지 {stage}', rect[0] + rect[2] / 2, 393, 16,
                      BLUE if stage == self.ranking_stage else LOBBY_MUTED, center=True)
        self.art('crown_icon', (516, 338, 26, 24))
        self.text('클리어 시간 랭킹', 550, 351, 20, max_width=220)
        self.text('빠른 순 · 닉네임별 최고 기록', 641, 327, 12, LOBBY_MUTED, center=True)
        self.art('badge', (512, 294, 258, 25), stretch=True)
        self.text('순위', 535, 307, 12, center=True)
        self.text('닉네임', 615, 307, 12, center=True)
        self.text('완료 시간', 722, 307, 12, center=True)
        rows = self.session.records.ranking(self.ranking_stage)
        pages = max(1, (len(rows) + RANK_PAGE_SIZE - 1) // RANK_PAGE_SIZE)
        self.ranking_page = min(self.ranking_page, pages - 1)
        start = self.ranking_page * RANK_PAGE_SIZE
        for index, (name, elapsed) in enumerate(rows[start:start + RANK_PAGE_SIZE], start):
            cy = 280 - (index - start) * 27
            color = BLUE if name == self.session.nickname else NAVY
            if name == self.session.nickname:
                rounded_box((512, cy - 12, 258, 24), LOBBY_STAGE, 5)
            rank = next(i + 1 for i, row in enumerate(rows) if row[1] == elapsed)
            self.text(str(rank), 535, cy, 14, color, center=True, max_width=38)
            self.text(name, 615, cy, 14, color, center=True, max_width=100)
            self.text(format_time(elapsed), 722, cy, 14, color, center=True)
        if not rows:
            self.text('아직 완료 기록이 없어요', 641, 250, 15, LOBBY_MUTED, center=True)
            self.text('첫 기록에 도전해 보세요!', 641, 222, 13, LOBBY_MUTED, center=True)
        self.button(RANK_PREVIOUS, '<', mouse, enabled=self.ranking_page > 0, size=13)
        self.button(RANK_NEXT, '>', mouse, enabled=self.ranking_page < pages - 1, size=13)
        self.text(f'{self.ranking_page + 1} / {pages}', 641, 177, 12, LOBBY_MUTED, center=True)
        rounded_box((515, 157, 251, 1), border, 0)
        best = self.session.records.best(self.ranking_stage, self.session.nickname)
        self.text('내 최고 기록', 519, 135, 14)
        self.text(format_time(best) if best is not None else '미완료', 715, 135, 16, BLUE, center=True)

    def draw_preview(self, mouse, ending=False):
        rounded_box((0, 0, WIDTH, HEIGHT), LOBBY_BACKGROUND, 0)
        self.art("panel_flat", (105, 105, 590, 415), stretch=True)
        self.art("market_banner", (135, 336, 530, 116))
        if ending:
            self.text("완료 화면 미리보기 / 개발 전용", 400, 490, 16, BLUE, center=True)
            self.text("장보기 완료!", 400, 300, 28, center=True)
            self.text("더 빠른 시간으로 최고 기록에 도전하세요.", 400, 257, 18, center=True)
            self.text("스테이지별 랭킹에서 내 기록을 확인할 수 있어요.", 400, 229, 18, center=True)
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
