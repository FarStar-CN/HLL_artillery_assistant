import math
import unittest

from logic import (
    clamp_distance,
    clamp_to_sector,
    compute_mil,
    compute_target_position,
    nearest_cardinal_heading,
    relative_angle,
)


class LogicTests(unittest.TestCase):
    def test_clamp_distance(self):
        self.assertEqual(clamp_distance(50, 100, 1600), 100)
        self.assertEqual(clamp_distance(2000, 100, 1600), 1600)
        self.assertEqual(clamp_distance(800, 100, 1600), 800)

    def test_clamp_to_sector(self):
        self.assertEqual(clamp_to_sector(10, 0, 15), 10)
        self.assertEqual(clamp_to_sector(40, 0, 15), 15)
        self.assertEqual(clamp_to_sector(340, 0, 15), 345)

    def test_compute_target_position(self):
        x_value, y_value = compute_target_position(100, 100, 100, 90, 2)
        self.assertAlmostEqual(x_value, 300.0)
        self.assertAlmostEqual(y_value, 100.0)

    def test_relative_angle(self):
        self.assertEqual(relative_angle(10, 350), 20)
        self.assertEqual(relative_angle(350, 10), -20)
        self.assertEqual(relative_angle(20, None), 0.0)

    def test_compute_mil(self):
        expected = 1002.0 - 1500.0 / (1500.0 / 356.0)
        self.assertAlmostEqual(compute_mil(1500.0), expected)

    def test_nearest_cardinal_heading(self):
        heading = nearest_cardinal_heading(100, 0, 1000, 1000)
        self.assertTrue(math.isclose(heading, 180.0))


if __name__ == "__main__":
    unittest.main()
