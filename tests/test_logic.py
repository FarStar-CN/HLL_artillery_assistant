import unittest

from core.country import USA_SPG, USA_STD
from core.logic import (
    angle_from_points,
    clamp_distance,
    clamp_to_sector,
    compute_target_position,
    distance_from_mil,
    effective_distance as logic_effective_distance,
    interp_dist_to_mil,
    interp_mil_to_dist,
    mil_from_distance,
    point_distance,
    profile_compute_mil,
    profile_inverse_mil,
    project_point_to_ray,
    relative_angle,
    snap_to_cardinal,
)


class LogicTests(unittest.TestCase):
    # ── 几何工具 ──

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

    def test_snap_to_cardinal(self):
        self.assertEqual(snap_to_cardinal(20), 0)
        self.assertEqual(snap_to_cardinal(100), 90)

    def test_project_point_to_ray(self):
        x_value, y_value = project_point_to_ray(0, 0, 20, -20, 0)
        self.assertAlmostEqual(x_value, 0.0)
        self.assertAlmostEqual(y_value, -20.0)

    def test_point_distance(self):
        self.assertAlmostEqual(point_distance(0, 0, 3, 4), 5.0)

    # ── MIL ↔ 距离 线性公式 ──

    def test_mil_from_distance_std(self):
        expected = 1002.0 - 1500.0 / (1500.0 / 356.0)
        self.assertAlmostEqual(
            mil_from_distance(USA_STD.mil_base, USA_STD.mil_k, 1500.0), expected,
        )

    def test_distance_from_mil_std(self):
        d = distance_from_mil(USA_STD.mil_base, USA_STD.mil_k, 800)
        # roundtrip
        mil = mil_from_distance(USA_STD.mil_base, USA_STD.mil_k, d)
        self.assertAlmostEqual(mil, 800.0)

    def test_effective_distance_formula(self):
        self.assertAlmostEqual(
            logic_effective_distance(USA_STD.mil_k, 1000, 5), 1000 - USA_STD.mil_k * 5,
        )

    # ── SPG 线性公式 (mil_k < 0) ──

    def test_mil_from_distance_spg(self):
        # USA_SPG: MIL = (d - 50) / 1.5
        self.assertAlmostEqual(mil_from_distance(-33.333, -1.5, 200), 100, places=0)
        self.assertAlmostEqual(mil_from_distance(-33.333, -1.5, 600), 366.67, places=1)

    def test_distance_from_mil_spg(self):
        # USA_SPG: d = 1.5 * MIL + 50
        self.assertAlmostEqual(distance_from_mil(-33.333, -1.5, 100), 200, places=0)
        self.assertAlmostEqual(distance_from_mil(-33.333, -1.5, 366), 599, places=0)

    # ── 扩展段插值 ──

    def test_interp_mil_to_dist(self):
        table = USA_SPG.extended_range
        self.assertAlmostEqual(interp_mil_to_dist(table, 366), 600, places=0)
        self.assertAlmostEqual(interp_mil_to_dist(table, 441), 699, places=0)
        self.assertAlmostEqual(interp_mil_to_dist(table, 766), 915, places=0)
        # clamp beyond table
        self.assertAlmostEqual(interp_mil_to_dist(table, 800), 915, places=0)

    def test_interp_dist_to_mil(self):
        table = USA_SPG.extended_range
        self.assertEqual(interp_dist_to_mil(table, 600), 366)
        # clamp beyond table
        self.assertAlmostEqual(interp_dist_to_mil(table, 1000), 766, places=0)

    # ── Profile-aware 封装 ──

    def test_profile_compute_mil_std(self):
        mil = profile_compute_mil(USA_STD, 1000)
        self.assertAlmostEqual(mil, USA_STD.mil_base - 1000 / USA_STD.mil_k)

    def test_profile_compute_mil_spg_linear(self):
        self.assertAlmostEqual(profile_compute_mil(USA_SPG, 400), 233.33, places=1)

    def test_profile_compute_mil_spg_extended(self):
        self.assertEqual(profile_compute_mil(USA_SPG, 600), 366)
        self.assertEqual(profile_compute_mil(USA_SPG, 915), 766)

    def test_profile_inverse_mil_spg_linear(self):
        self.assertAlmostEqual(profile_inverse_mil(USA_SPG, 200), 350, places=0)

    def test_profile_inverse_mil_spg_extended(self):
        self.assertEqual(profile_inverse_mil(USA_SPG, 366), 600)
        self.assertEqual(profile_inverse_mil(USA_SPG, 766), 915)


if __name__ == "__main__":
    unittest.main()
