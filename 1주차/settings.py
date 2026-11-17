"""화면 크기와 리소스 경로. 실행 폴더와 무관하게 이미지를 찾는다."""
from pathlib import Path

WIDTH, HEIGHT = 800, 600
BUTTON_WIDTH, BUTTON_HEIGHT = 300, 100
BUTTON_MARGIN = 24
BUTTON_X = WIDTH - BUTTON_MARGIN - BUTTON_WIDTH / 2
BUTTON_Y = BUTTON_MARGIN + BUTTON_HEIGHT / 2
HOVER_SCALE = 1.08
ASSET_DIR = Path(__file__).resolve().parent
FONT_PATH = ASSET_DIR.parent / 'assets' / 'fonts' / 'Jua-Regular.ttf'
START_ASSET_DIR = ASSET_DIR / "start assets"
LOBBY_ASSET_DIR = ASSET_DIR / "lobby assets" / "images" / "lobby"
DEVELOPMENT_MODE = False

# 로비·미리보기 색상. 닉네임과 장보기 UI에 맞춘 크림색·파스텔 파랑.
LOBBY_BACKGROUND = (239, 242, 225)
LOBBY_PANEL = (255, 248, 230)
LOBBY_STAGE = (224, 239, 248)
LOBBY_LOCKED = (235, 237, 225)
LOBBY_ACCOUNT = (255, 248, 230)
LOBBY_MUTED = (67, 87, 117)

