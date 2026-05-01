import unittest

from settings import CELL_SIZE
from systems.fog import FogOfWar


class FogTests(unittest.TestCase):
    def test_reveal_circle_marks_cells_active_and_memory(self):
        fog = FogOfWar(10, 10, fade_time=3.0, vision_radius=1.2)
        fog.reveal_circle(5 * CELL_SIZE, 5 * CELL_SIZE, 2 * CELL_SIZE, duration=2.0)
        self.assertGreater(fog.revealed[5][5], 0)
        self.assertTrue(fog.is_remembered(5, 5))

    def test_update_fades_revealed_cells(self):
        fog = FogOfWar(6, 6, fade_time=1.0, vision_radius=1.0)
        fog.reveal_circle(3 * CELL_SIZE, 3 * CELL_SIZE, CELL_SIZE, duration=0.5)
        old_value = fog.revealed[3][3]
        fog.update(0.2)
        self.assertLess(fog.revealed[3][3], old_value)


if __name__ == "__main__":
    unittest.main()
