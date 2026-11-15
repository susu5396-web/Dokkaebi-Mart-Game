"""실제 SDL 이벤트와 렌더러로 로비 연결을 검증한다.

실행: python 1주차/test_lobby.py (pico2d 창을 잠시 열었다가 닫는다)
"""
import unittest

import pico2d

from main import Game, collect_events
from settings import WIDTH, HEIGHT, BUTTON_X, BUTTON_Y
from ui import CONFIRM
from lobby import STAGE_ONE, STAGE_TWO, PLAY, RETURN, LOGOUT, QUIT, PREVIEW


def click(rect=None, position=None):
    x, y = position or (rect[0] + rect[2] / 2, rect[1] + rect[3] / 2)
    event = pico2d.SDL_Event()
    event.type = pico2d.SDL_MOUSEBUTTONDOWN
    event.button.button = pico2d.SDL_BUTTON_LEFT
    event.button.x, event.button.y = int(x), int(HEIGHT - 1 - y)
    return event


def key(code, repeat=False):
    event = pico2d.SDL_Event()
    event.type = pico2d.SDL_KEYDOWN
    event.key.keysym.sym = code
    event.key.repeat = int(repeat)
    return event


def text(value, composition=False):
    event = pico2d.SDL_Event()
    if composition:
        event.type = pico2d.SDL_TEXTEDITING
        event.edit.text = value.encode("utf-8")
    else:
        event.type = pico2d.SDL_TEXTINPUT
        event.text.text = value.encode("utf-8")
    return event


class LobbyFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pico2d.open_canvas(WIDTH, HEIGHT)
        cls.game = Game(animate_transitions=False)
        collect_events()

    @classmethod
    def tearDownClass(cls):
        pico2d.SDL_StopTextInput()
        pico2d.close_canvas()

    def setUp(self):
        self.game.running = True
        self.game.lobby.development_mode = False
        self.game.request_scene("title")
        self.game.apply_transition()

    def enter_name(self):
        self.game.handle_events([click(position=(BUTTON_X, BUTTON_Y))])
        self.assertEqual(self.game.scene, "nickname")
        self.assertTrue(self.game.nickname_ui.focused)

    def enter_lobby(self):
        self.enter_name()
        self.game.handle_events([text("  은수  "), key(pico2d.SDLK_RETURN)])
        self.assertEqual(self.game.scene, "lobby")
        self.assertEqual(self.game.session.nickname, "은수")
        self.assertFalse(self.game.nickname_ui.focused)

    def test_empty_and_whitespace_do_not_enter_lobby(self):
        self.enter_name()
        for value in ("", "   "):
            self.game.nickname_ui.value = value
            self.game.handle_events([click(CONFIRM)])
            self.assertEqual(self.game.scene, "nickname")
            self.assertTrue(self.game.nickname_ui.error)

    def test_korean_composition_backspace_and_submit(self):
        self.enter_name()
        self.game.handle_events([text("은", composition=True), key(pico2d.SDLK_RETURN)])
        self.assertEqual(self.game.scene, "nickname")
        self.game.handle_events([text("은수님"), key(pico2d.SDLK_BACKSPACE), click(CONFIRM)])
        self.assertEqual(self.game.session.nickname, "은수")
        self.assertEqual(self.game.scene, "lobby")

    def test_length_limit_and_error_clear(self):
        self.enter_name()
        # SDL_TEXTINPUT은 이벤트당 UTF-8 31바이트까지 전달한다.
        self.game.handle_events([text("가나다라마바사"), text("아자차카타파하")])
        self.assertEqual(len(self.game.nickname_ui.value), 12)
        self.assertTrue(self.game.nickname_ui.error)
        self.game.handle_events([key(pico2d.SDLK_BACKSPACE)])
        self.assertFalse(self.game.nickname_ui.error)
        self.game.handle_events([click(CONFIRM)])
        self.assertEqual(len(self.game.session.nickname), 11)
        self.game.draw()  # 긴 한글 닉네임과 폰트 렌더링도 실행한다.

    def test_locked_stage_preserves_selection(self):
        self.enter_lobby()
        self.game.handle_events([click(STAGE_TWO)])
        self.assertIsNone(self.game.session.selected_stage)
        self.assertIn("완료하면", self.game.lobby.message)
        self.game.handle_events([click(STAGE_ONE), click(STAGE_TWO)])
        self.assertEqual(self.game.session.selected_stage, 1)
        self.assertEqual(self.game.scene, "lobby")

    def test_play_requires_selection_and_return_preserves_nickname(self):
        self.enter_lobby()
        self.game.handle_events([click(PLAY)])
        self.assertEqual(self.game.scene, "lobby")
        for _ in range(3):
            self.game.handle_events([click(STAGE_ONE), click(PLAY)])
            self.assertEqual(self.game.scene, "stage")
            self.assertEqual(self.game.session.selected_stage, 1)
            self.game.draw()
            self.game.handle_events([key(pico2d.SDLK_ESCAPE)])
            self.assertEqual(self.game.scene, "lobby")
            self.assertEqual(self.game.session.nickname, "은수")
            self.assertIsNone(self.game.session.selected_stage)
            self.assertFalse(self.game.session.stage2_unlocked)

    def test_transition_consumes_remaining_frame_input(self):
        self.enter_name()
        self.game.handle_events([text("은수"), click(CONFIRM), click(STAGE_ONE), click(PLAY)])
        self.assertEqual(self.game.scene, "lobby")
        self.assertIsNone(self.game.session.selected_stage)

    def test_logout_clears_all_session_and_input(self):
        self.enter_lobby()
        self.game.session.choose_stage(1)
        self.game.session.stage2_unlocked = True
        self.game.handle_events([click(LOGOUT)])
        self.assertEqual(self.game.scene, "title")
        self.assertEqual(self.game.session.nickname, "")
        self.assertEqual(self.game.nickname_ui.value, "")
        self.assertIsNone(self.game.session.selected_stage)
        self.assertFalse(self.game.session.stage2_unlocked)
        self.enter_name()
        self.assertEqual(self.game.nickname_ui.value, "")

    def test_developer_ending_is_gated_and_preserves_state(self):
        self.enter_lobby()
        self.game.handle_events([click(PREVIEW)])
        self.assertEqual(self.game.scene, "lobby")
        self.game.lobby.development_mode = True
        self.game.session.choose_stage(1)
        before = vars(self.game.session).copy()
        self.game.handle_events([click(PREVIEW)])
        self.assertEqual(self.game.scene, "ending")
        self.game.draw()
        self.game.handle_events([click(RETURN)])
        self.assertEqual(vars(self.game.session), before)

    def test_exit_button_escape_and_close(self):
        self.enter_lobby()
        self.game.handle_events([click(QUIT)])
        self.assertFalse(self.game.running)
        self.game.running = True
        self.game.handle_events([key(pico2d.SDLK_ESCAPE)])
        self.assertFalse(self.game.running)
        self.game.running = True
        event = pico2d.SDL_Event()
        event.type = pico2d.SDL_QUIT
        self.game.handle_events([click(STAGE_ONE), event])
        self.assertFalse(self.game.running)
        self.assertIsNone(self.game.session.selected_stage)

    def test_repeated_enter_does_not_submit(self):
        self.enter_name()
        self.game.handle_events([text("은수"), key(pico2d.SDLK_RETURN, repeat=True)])
        self.assertEqual(self.game.scene, "nickname")


if __name__ == "__main__":
    unittest.main(verbosity=2)
