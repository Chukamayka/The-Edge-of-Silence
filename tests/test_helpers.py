import unittest

from settings import CELL_SIZE
from utils.helpers import line_of_sight


class HelperTests(unittest.TestCase):
    def test_line_of_sight_blocked_by_wall(self):
        maze = [
            ["#", "#", "#", "#", "#"],
            ["#", ".", "#", ".", "#"],
            ["#", ".", "#", ".", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", "#", "#", "#", "#"],
        ]
        x1, y1 = 1.5 * CELL_SIZE, 1.5 * CELL_SIZE
        x2, y2 = 3.5 * CELL_SIZE, 1.5 * CELL_SIZE
        self.assertFalse(line_of_sight(x1, y1, x2, y2, maze))

    def test_line_of_sight_in_clear_corridor(self):
        maze = [
            ["#", "#", "#", "#", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", "#", "#", "#", "#"],
        ]
        x1, y1 = 1.5 * CELL_SIZE, 1.5 * CELL_SIZE
        x2, y2 = 3.5 * CELL_SIZE, 1.5 * CELL_SIZE
        self.assertTrue(line_of_sight(x1, y1, x2, y2, maze))


if __name__ == "__main__":
    unittest.main()
