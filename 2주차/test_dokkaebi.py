"""도깨비 속도, 우회 추적, 리스폰 회귀 검사."""
import unittest
from math import hypot
from market_dokkaebi import Dokkaebi, route, clear_path, spawn_dokkaebi, FOLLOW_DISTANCE
from market_world import Actor, can_stand, AISLE_CENTERS, DOKKAEBI_SPEED, PLAYER_WALK_SPEED, DOKKAEBI_DEN


class DokkaebiTests(unittest.TestCase):
    def test_speed_and_stage_spawns(self):
        self.assertEqual(DOKKAEBI_SPEED, PLAYER_WALK_SPEED + 5)
        for stage, count in ((1, 1), (2, 2)):
            enemies = spawn_dokkaebi(stage)
            self.assertEqual(len(enemies), count)
            for enemy in enemies:
                self.assertTrue(can_stand(enemy.x, enemy.y))
                self.assertGreater(enemy.x, 2000)
                self.assertLess(enemy.y, 200)
        enemy = Dokkaebi(2100, 500)
        enemy.update(.05, Actor(x=2100, y=1000))
        self.assertAlmostEqual(enemy.y - 500, 255 * .05)

    def test_routes_reach_all_aisles_without_crossing_obstacles(self):
        start = (2100, 100)
        for x in AISLE_CENTERS:
            for y in (300, 1000, 1800, 1950):
                with self.subTest(x=x, y=y):
                    path = route(start, (x, y))
                    self.assertTrue(path)
                    self.assertEqual(path[-1], (x, y))
                    last = start
                    for point in path:
                        self.assertTrue(clear_path(last, point))
                        last = point
        self.assertFalse(clear_path((100, 1000), (500, 1000)))

    def test_chase_round_shelf_and_checkout(self):
        enemy = spawn_dokkaebi(1)[0]
        for target in (Actor(x=100, y=1000), Actor(x=350, y=2100), Actor(x=500, y=2190)):
            for _ in range(1400):
                before = enemy.x, enemy.y
                enemy.update(.05, target)
                self.assertTrue(can_stand(enemy.x, enemy.y))
                self.assertTrue(clear_path(before, (enemy.x, enemy.y)))
                if hypot(enemy.x - target.x, enemy.y - target.y) <= FOLLOW_DISTANCE + .01:
                    break
            self.assertLessEqual(hypot(enemy.x - target.x, enemy.y - target.y), FOLLOW_DISTANCE + .01)
            enemy.update(.05, target)
            self.assertFalse(enemy.moving)

    def test_stolen_dokkaebi_flees_away_from_player(self):
        enemy = Dokkaebi(500, 1950, stolen_pid='milk', escape_in=5)
        target = Actor(x=350, y=1950)
        for _ in range(10):
            enemy.update(.05, target)
        self.assertGreater(enemy.x, 500)

    def test_two_enemies_do_not_overlap_and_wait_for_blocked_spawn(self):
        from market_dokkaebi import ENEMY_RADIUS, RESPAWN_DELAY
        enemies = spawn_dokkaebi(2)
        target = Actor(x=2100, y=1000)
        for _ in range(150):
            for enemy in enemies:
                enemy.update(.05, target, enemies)
            self.assertGreaterEqual(hypot(enemies[0].x - enemies[1].x, enemies[0].y - enemies[1].y), 2 * ENEMY_RADIUS - 1e-6)
        enemy = enemies[0]
        enemy.banish()
        target.x, target.y = 2100, 100
        enemy.update(RESPAWN_DELAY, target, enemies)
        self.assertEqual(enemy.phase, 'active')
        self.assertGreaterEqual(hypot(enemy.x - target.x, enemy.y - target.y), FOLLOW_DISTANCE)

    def test_new_round_respawns_at_den(self):
        enemies = spawn_dokkaebi(2)
        enemies[0].x = 500
        fresh = spawn_dokkaebi(2)
        self.assertGreater(fresh[0].x, 2000)
        self.assertEqual(fresh[0].animation, 0)


if __name__ == '__main__':
    unittest.main()
