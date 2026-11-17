"""실행: python -m unittest discover -s 2주차 -p test_market.py"""
import sys
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog import PRODUCTS
from market_state import MarketState
from market_world import Actor, SHELVES, SECTION_HEIGHT, can_stand


class RulesTests(unittest.TestCase):
    def test_stage_one_shopping_requirements(self):
        totals = set()
        for seed in range(200):
            state = MarketState(seed)
            with self.subTest(seed=seed):
                self.assertEqual(len(state.required), 5)
                self.assertEqual({PRODUCTS[pid].category for pid in state.required}, set(range(5)))
                self.assertTrue(all(count in (1, 2) for count in state.required.values()))
                total = sum(state.required.values())
                self.assertIn(total, (7, 8))
                totals.add(total)
                available = {pid for category in state.layout for section in category for pid in section}
                self.assertTrue(set(state.required) <= available)
                self.assertEqual(state.required, MarketState(seed).required)
        self.assertEqual(totals, {7, 8})

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
        self.assertAlmostEqual(normal.y - 500, 250 * .05)
        self.assertAlmostEqual(fast.y - 500, 400 * .05)
        actor = Actor(x=150, y=500)
        for _ in range(40):
            actor.move(1, 0, .05, True)
        self.assertLessEqual(actor.x, SHELVES[0][0] - 43)
        self.assertTrue(can_stand(actor.x, actor.y))
        self.assertEqual(actor.x, 100)

    def test_checkout_requires_exact_products_and_quantities(self):
        state = MarketState(3)
        pid = next(iter(state.required))
        state.inventory = dict(state.required)
        state.inventory[pid] -= 1
        self.assertEqual(state.checkout(), [(pid, 1)])
        self.assertIsNone(state.outcome)
        state.add(pid)
        extra = next(item for item in PRODUCTS if item not in state.required)
        state.add(extra)
        self.assertEqual(state.checkout(), [(extra, -1)])
        state.discard(extra)
        state.add(pid)
        self.assertEqual(state.checkout(), [(pid, -1)])
        state.discard(pid)
        self.assertEqual(state.checkout(), [])
        self.assertEqual(state.outcome, 'success')
        remaining = state.remaining
        state.update(5)
        state.add(extra)
        self.assertEqual(state.remaining, remaining)
        self.assertEqual(state.inventory, state.required)

    def test_timeout_prevents_success(self):
        state = MarketState(3)
        state.inventory = dict(state.required)
        state.update(240)
        state.checkout()
        self.assertEqual(state.outcome, 'timeout')

    def test_checkout_proximity(self):
        self.assertFalse(Actor().at_checkout())
        self.assertTrue(Actor(x=350, y=2100).at_checkout())
        self.assertFalse(Actor(x=450, y=2100).at_checkout())

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

    def setUp(self):
        from records import RecordBook
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.game.session.records = RecordBook(Path(temporary.name) / 'rankings.json')

    def test_checkout_retry_records_and_stage_unlock(self):
        game = self.game
        game.session.reset()
        game.session.login('기록테스트')
        game.session.selected_stage = 1
        game.request_scene('stage')
        game.apply_transition()
        market = game.market
        market.actor.x, market.actor.y = 350, 2100
        market.update(.01)
        self.assertTrue(market.differences)
        self.assertIsNone(market.state.outcome)
        self.assertIsNone(game.session.records.best(1, '기록테스트'))
        remaining = market.state.remaining
        market.update(.5)
        self.assertLess(market.state.remaining, remaining)
        market.state.inventory = dict(market.state.required)
        self.key(self.p.SDLK_e)
        self.assertEqual(market.state.outcome, 'success')
        self.assertEqual(game.session.records.best(1, '기록테스트'), 510)
        self.assertTrue(game.session.stage2_unlocked)
        market.inspect_cart()
        market.update(1)
        self.assertEqual(game.session.records.best(1, '기록테스트'), 510)
        game.draw()
        self.key(self.p.SDLK_RETURN)
        self.assertEqual(game.scene, 'lobby')
        game.session.choose_stage(2)
        game.request_scene('stage')
        game.apply_transition()
        market.actor.x, market.actor.y = 350, 2100
        market.state.inventory = dict(market.state.required)
        market.update(.01)
        self.assertEqual(game.session.records.best(2, '기록테스트'), 10)
        self.key(self.p.SDLK_RETURN)
        self.assertEqual(game.scene, 'lobby')
        game.draw()
        game.session.reset()

    def test_timeout_has_no_record_and_accepts_result_button(self):
        game = self.game
        game.session.reset()
        game.request_scene('stage')
        game.apply_transition()
        game.market.state.remaining = .001
        game.market.update(.01)
        self.assertEqual(game.market.state.outcome, 'timeout')
        self.assertEqual(game.session.records.ranking(1), [])
        game.draw()
        from market_result import RESULT_BUTTON
        event = self.p.SDL_Event()
        event.type = self.p.SDL_MOUSEBUTTONDOWN
        event.button.button = self.p.SDL_BUTTON_LEFT
        event.button.x = int(RESULT_BUTTON[0] + 10)
        event.button.y = int(RESULT_BUTTON[1] + 10)
        game.handle_events([event])
        self.assertEqual(game.scene, 'lobby')

    def test_dokkaebi_stage_reset_and_result_freeze(self):
        game = self.game
        game.session.reset()
        game.session.stage2_unlocked = True
        game.session.choose_stage(2)
        game.request_scene('stage')
        game.apply_transition()
        market = game.market
        self.assertEqual(len(market.dokkaebi), 2)
        start = [(enemy.x, enemy.y) for enemy in market.dokkaebi]
        market.update(.05)
        self.assertNotEqual(start, [(enemy.x, enemy.y) for enemy in market.dokkaebi])
        market.shelf = (0, 0, -1)
        before = [(enemy.x, enemy.y) for enemy in market.dokkaebi]
        market.update(.05)
        self.assertNotEqual(before, [(enemy.x, enemy.y) for enemy in market.dokkaebi])
        market.state.outcome = 'success'
        before = [(enemy.x, enemy.y) for enemy in market.dokkaebi]
        market.update(.05)
        self.assertEqual(before, [(enemy.x, enemy.y) for enemy in market.dokkaebi])
        game.session.reset()
        market.reset()
        self.assertEqual(len(market.dokkaebi), 1)
        self.assertEqual((market.dokkaebi[0].x, market.dokkaebi[0].y), (2100, 100))
        game.draw()

    def encounter(self, stage=1):
        game = self.game
        game.session.reset()
        game.session.stage2_unlocked = True
        game.session.choose_stage(stage)
        game.request_scene('stage')
        game.apply_transition()
        market = game.market
        market.actor.x, market.actor.y = 500, 1950
        market.dokkaebi[0].x, market.dokkaebi[0].y = 620, 1950
        if stage == 2:
            market.dokkaebi[1].x, market.dokkaebi[1].y = 380, 1950
        return market

    def test_theft_once_per_enemy_and_recovery_with_r(self):
        market = self.encounter(2)
        pid = next(iter(market.state.required))
        for _ in range(5):
            market.state.add(pid)
        required = dict(market.state.required)
        market.update(.01)
        self.assertEqual(market.state.inventory[pid], 3)
        self.assertTrue(all(enemy.stolen_pid == pid for enemy in market.dokkaebi))
        for _ in range(40):
            market.update(.05)
        self.assertEqual(market.state.inventory[pid], 3)
        self.key(self.p.SDLK_r)
        self.assertEqual(market.state.inventory[pid], 5)
        self.assertTrue(all(enemy.phase == 'vanishing' for enemy in market.dokkaebi))
        self.key(self.p.SDLK_r, repeat=True)
        self.assertEqual(market.state.inventory[pid], 5)
        self.assertEqual(market.state.required, required)
        self.game.draw()
        for _ in range(99):
            market.update(.05)
        self.assertTrue(all(enemy.phase == 'hidden' for enemy in market.dokkaebi))
        market.update(.05)
        self.assertTrue(all(enemy.phase == 'active' for enemy in market.dokkaebi))
        self.assertTrue(all(enemy.x > 2000 for enemy in market.dokkaebi))

    def test_thief_escapes_after_five_seconds_and_respawns(self):
        market = self.encounter()
        pid = next(iter(market.state.required))
        market.state.add(pid)
        market.state.add(pid)
        market.update(.01)
        enemy = market.dokkaebi[0]
        for _ in range(99):
            market.update(.05)
        self.assertEqual(enemy.phase, 'active')
        self.assertEqual(market.state.inventory[pid], 1)
        market.update(.05)
        self.assertEqual(enemy.phase, 'vanishing')
        self.assertIsNone(enemy.stolen_pid)
        self.key(self.p.SDLK_r)
        self.assertEqual(market.state.inventory[pid], 1)
        for _ in range(100):
            market.update(.05)
        self.assertEqual(enemy.phase, 'active')
        self.assertGreater(enemy.x, 2000)

    def test_entity_collision_and_empty_cart(self):
        from math import hypot
        from market_dokkaebi import FOLLOW_DISTANCE
        market = self.encounter()
        enemy = market.dokkaebi[0]
        market.keys.update((self.p.SDLK_d, self.p.SDLK_LSHIFT))
        for _ in range(20):
            market.update(.05)
            self.assertGreaterEqual(hypot(enemy.x - market.actor.x, enemy.y - market.actor.y), FOLLOW_DISTANCE - 1e-5)
        self.assertIsNone(enemy.stolen_pid)
        market.actor.x, market.actor.y = 140, 1000
        enemy.x, enemy.y = 450, 1000
        self.key(self.p.SDLK_r)
        self.assertEqual(enemy.phase, 'active')
        self.game.session.reset()

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
        # 매대뷰에서도 오른쪽 카트 클릭은 담기가 아닌 1개 버리기다.
        rect, _ = market.hud.slots(market.state)[0]
        event.button.x, event.button.y = int(rect[0] + 5), int(rect[1] + 5)
        game.handle_events([event])
        self.assertEqual(market.state.inventory[pid], 2)
        self.assertIsNotNone(market.shelf)
        market.state.add(pid)
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
        from market_hud import CART_RECT
        market.hud.scroll(-1, CART_RECT[0] + 20, CART_RECT[1] + 20, market.state)
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

    def test_fade_fixed_window_and_input_pause(self):
        import ctypes
        p, game = self.p, self.game
        game.request_scene('lobby')
        game.apply_transition()
        prepared_market = game.market
        width, height = ctypes.c_int(), ctypes.c_int()
        p.SDL_GetWindowSize(p.open_canvas.__globals__['window'], ctypes.byref(width), ctypes.byref(height))
        self.assertEqual((width.value, height.value), (950, 622))
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
            self.assertIs(game.market, prepared_market)
            width, height = ctypes.c_int(), ctypes.c_int()
            p.SDL_GetWindowSize(p.open_canvas.__globals__['window'], ctypes.byref(width), ctypes.byref(height))
            self.assertEqual((width.value, height.value), (950, 622))
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
