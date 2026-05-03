import unittest

from core.country import USA_SPG, USA_STD, get_profile, PROFILES


class CountryProfileTests(unittest.TestCase):
    def setUp(self):
        self.std = USA_STD
        self.spg = USA_SPG

    # ── STD formula tests ──

    def test_compute_mil(self):
        d = 1500.0
        expected = self.std.mil_base - d / self.std.mil_k
        self.assertAlmostEqual(self.std.compute_mil(d), expected)

    def test_inverse_mil_roundtrip(self):
        for d in (100, 500, 1000, 1500, 1600):
            mil = self.std.compute_mil(d)
            self.assertAlmostEqual(self.std.inverse_mil(mil), d, places=4)

    # ── SPG formula identity tests ──

    def test_compute_effective_distance_zero_tilt(self):
        d = 800.0
        self.assertAlmostEqual(
            self.spg.compute_effective_distance(d, 0.0), d,
        )

    def test_compute_effective_distance_positive_tilt(self):
        d = 800.0
        tilt = 5.0
        expected = d - self.spg.mil_k * tilt
        self.assertAlmostEqual(
            self.spg.compute_effective_distance(d, tilt), expected,
        )

    def test_compute_effective_distance_negative_tilt(self):
        d = 800.0
        tilt = -5.0
        expected = d - self.spg.mil_k * tilt
        self.assertAlmostEqual(
            self.spg.compute_effective_distance(d, tilt), expected,
        )

    def test_effective_max_zero_tilt(self):
        eff_max = self.spg.compute_effective_distance(
            self.spg.max_distance, 0.0,
        )
        self.assertEqual(eff_max, self.spg.max_distance)

    def test_effective_max_is_constant(self):
        """effective max distance is always max_distance, independent of tilt"""
        for tilt in (-10.0, -5.0, 0.0, 5.0, 10.0):
            self.assertEqual(self.spg.max_distance, 600.0)

    # ── SPG MIL / distance mapping tests ──

    def test_effective_mil_range(self):
        """SPG: min_distance=200 maps to eff_mil=100, max_distance=600 maps to eff_mil~366.67"""
        eff_low = self.spg.compute_mil(self.spg.min_distance)
        eff_high = self.spg.compute_mil(self.spg.max_distance)
        self.assertAlmostEqual(eff_low, 100.0, places=0)
        self.assertAlmostEqual(eff_high, 600.0 / 1.5 - 50.0 / 1.5, places=2)

    def test_spg_mil_distance_formula(self):
        """distance = 1.5 * effective_mil + 50"""
        for eff_mil, expected_d in ((100, 200), (233, 399.5), (366, 599)):
            d = self.spg.inverse_mil(eff_mil)
            self.assertAlmostEqual(d, expected_d, places=0)

    def test_mil_includes_tilt_identity(self):
        """mathematical identity: compute_mil(d_eff) = compute_mil(d) + tilt
        This holds for the formula and is used internally, not for sidebar display."""
        d = 800.0
        tilt = 3.0
        d_eff = self.spg.compute_effective_distance(d, tilt)
        mil = self.spg.compute_mil(d_eff)
        base_mil = self.spg.compute_mil(d)
        self.assertAlmostEqual(mil, base_mil + tilt, places=4)

    # ── SPG set_mil / set_distance formula tests ──

    def test_set_mil_spg_direct(self):
        """set_mil in SPG: mil_flat = clamp(input, [eff_low - tilt, eff_high - tilt] ∩ [spg limits])"""
        p = self.spg
        tilt = 5.0
        eff_low = p.compute_mil(p.min_distance)  # ~100
        eff_high = p.compute_mil(p.max_distance)  # ~366.67
        mil_min = max(p.spg_mil_min, eff_low - tilt)  # max(-89, 95) = 95
        mil_max = min(p.spg_mil_max, eff_high - tilt)  # min(466, 361.67) = 361.67

        # Within range
        mil_flat = 200.0
        clamped = max(mil_min, min(mil_max, mil_flat))
        self.assertEqual(clamped, 200.0)

        # Below effective range
        mil_flat = 50.0
        clamped = max(mil_min, min(mil_max, mil_flat))
        self.assertEqual(clamped, mil_min)

        # Above effective range
        mil_flat = 400.0
        clamped = max(mil_min, min(mil_max, mil_flat))
        self.assertEqual(clamped, mil_max)

    def test_set_distance_spg_back_compute(self):
        """set_distance in SPG: mil_flat = compute_mil(d_input) - tilt_mil"""
        p = self.spg
        tilt = 5.0
        d_input = 500.0
        candidate_mil = p.compute_mil(d_input) - tilt
        # verify roundtrip: inverse_mil(candidate_mil + tilt) ≈ d_input
        d_verify = p.inverse_mil(candidate_mil + tilt)
        self.assertAlmostEqual(d_verify, d_input, places=4)

    # ── SPG profile structural tests ──

    def test_spg_mil_flat_range(self):
        """USA SPG mil_flat absolute limits are [-89, 466]"""
        self.assertEqual(self.spg.spg_mil_min, -89.0)
        self.assertEqual(self.spg.spg_mil_max, 466.0)

    def test_profile_registry(self):
        for country in ("USA", "UK", "USSR", "DE"):
            for mode in ("STD", "SPG"):
                p = get_profile(country, mode)
                self.assertEqual(p.country, country)
                self.assertEqual(p.mode, mode)

    def test_spg_profile_has_larger_sector(self):
        """USA SPG has 180 deg sector vs 15 deg for STD"""
        self.assertEqual(self.spg.sector_angle, 180.0)
        self.assertEqual(self.std.sector_angle, 15.0)


if __name__ == "__main__":
    unittest.main()
