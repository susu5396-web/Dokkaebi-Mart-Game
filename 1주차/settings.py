"""화면 크기와 리소스 경로. 실행 폴더와 무관하게 이미지를 찾는다."""
from pathlib import Path

WIDTH, HEIGHT = 800, 600
BUTTON_WIDTH, BUTTON_HEIGHT = 300, 100
BUTTON_MARGIN = 24
BUTTON_X = WIDTH - BUTTON_MARGIN - BUTTON_WIDTH / 2
BUTTON_Y = BUTTON_MARGIN + BUTTON_HEIGHT / 2
HOVER_SCALE = 1.08
ASSET_DIR = Path(__file__).resolve().parent
START_ASSET_DIR = ASSET_DIR / "start assets"
LOBBY_ASSET_DIR = ASSET_DIR / "lobby assets" / "images" / "lobby"
DEVELOPMENT_MODE = False

# 로비·미리보기 색상. 흰 외곽선이 있는 에셋과 구분되는 연한 네이비 계열.
LOBBY_BACKGROUND = (207, 220, 237)
LOBBY_PANEL = (192, 208, 230)
LOBBY_STAGE = (167, 190, 220)
LOBBY_LOCKED = (184, 198, 217)
LOBBY_ACCOUNT = (224, 234, 248)
LOBBY_MUTED = (67, 87, 117)
