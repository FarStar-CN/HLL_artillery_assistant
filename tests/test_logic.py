import unittest

from country import USA_STD
from logic import (
    angle_from_points,
    clamp_distance,
    clamp_to_sector,
    compute_target_position,
    point_distance,
    project_point_to_ray,
    relative_angle,
    snap_to_cardinal,
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

    def test_angle_from_points(self):
        self.assertAlmostEqual(angle_from_points(0, 0, 0, -10), 0.0)
        self.assertAlmostEqual(angle_from_points(0, 0, 10, 0), 90.0)

    def test_relative_angle(self):
        self.assertEqual(relative_angle(10, 350), 20)
        self.assertEqual(relative_angle(350, 10), -20)
        self.assertEqual(relative_angle(20, None), 0.0)

    def test_compute_mil(self):
        expected = 1002.0 - 1500.0 / (1500.0 / 356.0)
        self.assertAlmostEqual(USA_STD.compute_mil(1500.0), expected)

    def test_snap_to_cardinal(self):
        self.assertEqual(snap_to_cardinal(20), 0)
        self.assertEqual(snap_to_cardinal(100), 90)

    def test_project_point_to_ray(self):
        x_value, y_value = project_point_to_ray(0, 0, 20, -20, 0)
        self.assertAlmostEqual(x_value, 0.0)
        self.assertAlmostEqual(y_value, -20.0)

    def test_point_distance(self):
        self.assertAlmostEqual(point_distance(0, 0, 3, 4), 5.0)


if __name__ == "__main__":
    unittest.main()
