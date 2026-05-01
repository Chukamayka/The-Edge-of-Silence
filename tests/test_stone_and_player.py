import unittest
from collections import defaultdict
from unittest.mock import patch

import pygame

from entities.player import Player
from entities.stone import Stone
from settings import CELL_SIZE


class StoneAndPlayerTests(unittest.TestCase):
    def test_stone_bounce_reduces_bounces_left(self):
        stone = Stone()
        maze = [
            ["#", "#", "#", "#", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", "#", "#", "#", "#"],
        ]
        stone.charge_power = 1.0
        stone.throw(2.5 * CELL_SIZE, 2.5 * CELL_SIZE, 4.5 * CELL_SIZE, 2.5 * CELL_SIZE)
        before = stone.bounces_left
        for _ in range(40):
            stone.update(1 / 60, maze)
            if stone.just_bounced:
                break
        self.assertLess(stone.bounces_left, before)

    def test_player_dies_when_pushing_into_wall(self):
        pygame.init()
        maze = [
            ["#", "#", "#", "#", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", ".", "#", ".", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", "#", "#", "#", "#"],
        ]
        player = Player(1.95 * CELL_SIZE, 2.5 * CELL_SIZE)
        keys = defaultdict(bool)
        keys[pygame.K_d] = True
        with patch("pygame.key.get_pressed", return_value=keys):
            for _ in range(40):
                pressed = pygame.key.get_pressed()
                player.update(pressed, maze, 1 / 60, camera=None)
                if not player.alive:
                    break
        self.assertFalse(player.alive)


if __name__ == "__main__":
    unittest.main()
