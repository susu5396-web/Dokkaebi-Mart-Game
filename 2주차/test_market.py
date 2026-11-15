"""실행: python -m unittest discover -s 2주차 -p test_market.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog import PRODUCTS
from market_state import MarketState
from market_world import Actor, SHELVES, SECTION_HEIGHT, can_stand


class RulesTests(unittest.TestCase):
    def test_layout_and_groups(self):
        state = MarketState(12)
        flattened = [pid for category in state.layout for section in category for pid in section]
        self.assertEqual(len(flattened), 160)
        self.assertEqual(set(flattened), set(PRODUCTS))
        for category in state.layout:
            self.assertEqual(len(category), 8)
            for section in category:
                self.assertEqual(len({PRODUCTS[pid].group for pid in section}), 1)
        self.assertEqual(state.layout, MarketState(12).layout)

    def test_inventory_does_not_modify_requirements(self):
        state = MarketState(3)
        required = dict(state.required)
        pid = next(pid for pid in PRODUCTS if pid not in required)
        for _ in range(3):
            state.add(pid)
        state.discard(pid)
        self.assertEqual(state.inventory[pid], 2)
        state.discard(pid)
        state.discard(pid)
        state.discard(pid)
        self.assertNotIn(pid, state.inventory)
        self.assertEqual(required, state.required)

    def test_movement_and_collision(self):
        normal, fast = Actor(x=100, y=500), Actor(x=100, y=500)
        normal.move(0, 1, .05)
        fast.move(0, 1, .05, True)
        self.assertGreater(fast.y, normal.y)
        actor = Actor(x=150, y=500)
        for _ in range(40):
            actor.move(1, 0, .05, True)
        self.assertLessEqual(actor.x, SHELVES[0][0] - 43)
        self.assertTrue(can_stand(actor.x, actor.y))
        self.assertEqual(actor.x, 100)

    def test_timer_warning_boundary(self):
        from market_hud import timer_color
        self.assertEqual(timer_color(60), (40, 61, 83))
        self.assertEqual(timer_color(59.9), (205, 45, 46))


class SceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pico2d as p
        cls.p = p
        p.open_canvas(800, 600)
        from main import Game
        cls.game = Game(animate_transitions=False)

    @classmethod
    def tearDownClass(cls):
        cls.p.close_canvas()

    def key(self, code, up=False, repeat=False):
        p = self.p
        event = p.SDL_Event()
        event.type = p.SDL_KEYUP if up else p.SDL_KEYDOWN
        event.key.keysym.sym = code
        event.key.repeat = repeat
        self.game.handle_events([event])

    def test_shopping_round_trip(self):
        p, game = self.p, self.game
        game.request_scene('stage')
        game.apply_transition()
        market = game.market
        self.assertEqual(len(market.sprite.frames), 54)
        self.assertGreater(market.sprite.frames[0, 0][3], 150)
        self.assertGreater(market.sprite.frames[2, 0][3], 140)
        game.update(.01)
        game.draw()
        p.update_canvas()
        market.actor.align(0, 2, -1)
        self.key(p.SDLK_e)
        self.assertEqual(market.shelf[:2], (0, 2))
        previous_y = market.actor.y
        self.key(p.SDLK_w)
        self.assertEqual(market.shelf[1], 1)
        self.assertEqual(market.actor.y, previous_y - SECTION_HEIGHT)
        self.key(p.SDLK_UP)
        self.assertEqual(market.shelf[1], 1)
        self.key(p.SDLK_w, up=True)
        self.key(p.SDLK_UP, up=True)
        self.key(p.SDLK_w, repeat=True)
        self.assertEqual(market.shelf[1], 1)
        event = p.SDL_Event()
        event.type = p.SDL_MOUSEBUTTONDOWN
        event.button.button = p.SDL_BUTTON_LEFT
        event.button.x, event.button.y = 180, 450
        game.handle_events([event, event, event])
        pid = market.state.layout[0][1][0]
        self.assertEqual(market.state.inventory[pid], 3)
        before = market.state.remaining
        game.update(.25)
        self.assertLess(market.state.remaining, before)
        game.draw()
        p.update_canvas()
        self.key(p.SDLK_ESCAPE)
        self.assertIsNone(market.shelf)
        self.assertTrue(game.running)
        rect, _ = market.hud.slots(market.state)[0]
        market.hud.click(rect[0] + 5, rect[1] + 5, market.state)
        self.assertEqual(market.state.inventory[pid], 2)
        for product in list(PRODUCTS)[:10]:
            market.state.add(product)
        market.hud.scroll(-1, 1000, 800, market.state)
        self.assertEqual(market.hud.offset, 3)
        game.draw()
        p.update_canvas()
        self.key(p.SDLK_ESCAPE)
        self.assertEqual(game.scene, 'lobby')
        game.draw()
        p.update_canvas()
        game.request_scene('stage')
        game.apply_transition()
        self.assertEqual(game.market.state.inventory, {})

    def test_fade_resize_and_input_pause(self):
        import ctypes
        p, game = self.p, self.game
        game.request_scene('lobby')
        game.apply_transition()
        game.animate_transitions = True
        try:
            game.request_scene('stage')
            game.apply_transition()
            self.assertEqual(game.scene, 'lobby')
            game.update(.25)
            self.assertEqual(game.fade_phase, 'switch')
            game.draw()
            p.update_canvas()
            game.update(.01)
            self.assertEqual(game.scene, 'stage')
            width, height = ctypes.c_int(), ctypes.c_int()
            p.SDL_GetWindowSize(p.open_canvas.__globals__['window'], ctypes.byref(width), ctypes.byref(height))
            self.assertEqual((width.value, height.value), (1000, 720))
            remaining = game.market.state.remaining
            self.key(p.SDLK_w)
            self.assertFalse(game.market.keys)
            game.update(.1)
            game.draw()
            p.update_canvas()
            self.assertEqual(game.market.state.remaining, remaining)
            game.update(.25)
            self.assertIsNone(game.fade_phase)
            game.update(.1)
            self.assertLess(game.market.state.remaining, remaining)
        finally:
            game.animate_transitions = False
            game.fade_phase = None
            game.pending_scene = None


if __name__ == '__main__':
    unittest.main()
