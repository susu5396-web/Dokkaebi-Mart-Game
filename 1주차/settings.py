"""화면 크기와 리소스 경로. 실행 폴더와 무관하게 이미지를 찾는다."""
from pathlib import Path

WIDTH, HEIGHT = 800, 600
BUTTON_WIDTH, BUTTON_HEIGHT = 300, 100
BUTTON_MARGIN = 24
BUTTON_X = WIDTH - BUTTON_MARGIN - BUTTON_WIDTH / 2
BUTTON_Y = BUTTON_MARGIN + BUTTON_HEIGHT / 2
HOVER_SCALE = 1.08
ASSET_DIR = Path(__file__).resolve().parent
LOBBY_ASSET_DIR = ASSET_DIR / "assets" / "images" / "lobby"
DEVELOPMENT_MODE = False
