import unittest

from systems.maze import MazeGenerator


class MazeTests(unittest.TestCase):
    def test_maze_has_start_and_exit(self):
        maze = MazeGenerator(31, 31, 2).generate()
        flat = [cell for row in maze for cell in row]
        self.assertIn("S", flat)
        self.assertIn("E", flat)

    def test_maze_dimensions_are_consistent(self):
        maze = MazeGenerator(31, 31, 2).generate()
        self.assertGreater(len(maze), 0)
        width = len(maze[0])
        self.assertTrue(all(len(row) == width for row in maze))


if __name__ == "__main__":
    unittest.main()
