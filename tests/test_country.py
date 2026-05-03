import unittest

from core.country import USA_SPG, USA_STD, get_profile, PROFILES
from core.logic import interp_mil_to_dist


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
        self.assertEqual(self.spg.max_distance, 915.0)

    # ── SPG standard range (linear) tests ──

    def test_effective_mil_range(self):
        """SPG: min_distance=200 → 100MIL, max_distance=915 → 766MIL (extended)"""
        eff_low = self.spg.compute_mil(self.spg.min_distance)
        eff_high = self.spg.compute_mil(self.spg.max_distance)
        self.assertAlmostEqual(eff_low, 100.0, places=0)
        self.assertEqual(eff_high, 766.0)

    def test_spg_mil_distance_formula_linear(self):
        """standard regime: distance = 1.5 * MIL + 50"""
        for eff_mil, expected_d in ((100, 200), (200, 350), (350, 575)):
            d = self.spg.inverse_mil(eff_mil)
            self.assertAlmostEqual(d, expected_d, places=0)
        # at boundary (366 MIL), interpolation table gives 600 (game value)
        self.assertEqual(self.spg.inverse_mil(366), 600.0)

    def test_mil_includes_tilt_identity(self):
        """mathematical identity in linear regime: compute_mil(d_eff) = compute_mil(d) + tilt"""
        d = 500.0  # within linear range (< 600)
        tilt = 3.0
        d_eff = self.spg.compute_effective_distance(d, tilt)
        mil = self.spg.compute_mil(d_eff)
        base_mil = self.spg.compute_mil(d)
        self.assertAlmostEqual(mil, base_mil + tilt, places=4)

    # ── SPG extended range tests ──

    def test_extended_range_table(self):
        """verify each data point in the extended range table"""
        for eff_mil, expected_d in self.spg.extended_range:
            d = self.spg.inverse_mil(eff_mil)
            self.assertAlmostEqual(d, expected_d, places=0)

    def test_extended_range_interpolation(self):
        """linear interpolation between table points"""
        # midpoint between 416(666) and 466(732): MIL=441 → dist=699
        d = self.spg.inverse_mil(441)
        self.assertAlmostEqual(d, 699.0, places=0)

        # midpoint between 666(879) and 716(905): MIL=691 → dist=892
        d = self.spg.inverse_mil(691)
        self.assertAlmostEqual(d, 892.0, places=0)

    def test_extended_range_boundary_continuity(self):
        """boundary between linear and extended regimes within 1m"""
        # linear formula at 366 MIL gives 599, table gives 600
        d_linear = self.spg.mil_k * (self.spg.mil_base - 366)
        d_interp = interp_mil_to_dist(self.spg.extended_range, 366)
        self.assertAlmostEqual(d_linear, 599, places=0)
        self.assertAlmostEqual(d_interp, 600, places=0)
        # interpolation takes precedence at boundary
        self.assertEqual(self.spg.inverse_mil(366), 600.0)
        self.assertEqual(self.spg.compute_mil(600), 366.0)

    def test_extended_range_roundtrip(self):
        """MIL → distance → MIL roundtrip in extended regime"""
        for eff_mil in (416, 516, 616, 716):
            d = self.spg.inverse_mil(eff_mil)
            mil_back = self.spg.compute_mil(d)
            self.assertAlmostEqual(mil_back, eff_mil, places=0)

    def test_extended_range_clamp(self):
        """values beyond the table are clamped to the endpoint"""
        self.assertAlmostEqual(self.spg.inverse_mil(800), 915.0, places=0)
        self.assertAlmostEqual(self.spg.compute_mil(1000), 766.0, places=0)

    # ── SPG set_mil / set_distance formula tests ──

    def test_set_mil_spg_direct(self):
        """set_mil in SPG: mil_flat clamped to game mechanical limits [-89, 466]"""
        p = self.spg

        # Within range
        clamped = max(p.spg_mil_min, min(p.spg_mil_max, 200.0))
        self.assertEqual(clamped, 200.0)

        # Below mechanical limit
        clamped = max(p.spg_mil_min, min(p.spg_mil_max, -100.0))
        self.assertEqual(clamped, -89.0)

        # Above mechanical limit
        clamped = max(p.spg_mil_min, min(p.spg_mil_max, 500.0))
        self.assertEqual(clamped, 466.0)

    def test_set_mil_allows_below_100(self):
        """set_mil in SPG allows mil_flat below 100 (down to -89)"""
        p = self.spg
        clamped = max(p.spg_mil_min, min(p.spg_mil_max, 0.0))
        self.assertEqual(clamped, 0.0)
        clamped = max(p.spg_mil_min, min(p.spg_mil_max, -50.0))
        self.assertEqual(clamped, -50.0)

    def test_set_distance_spg_back_compute(self):
        """set_distance in SPG: mil_flat = compute_mil(d_input) - tilt_mil"""
        p = self.spg
        tilt = 5.0
        d_input = 500.0  # linear regime
        candidate_mil = p.compute_mil(d_input) - tilt
        d_verify = p.inverse_mil(candidate_mil + tilt)
        self.assertAlmostEqual(d_verify, d_input, places=4)

    def test_set_distance_extended_back_compute(self):
        """set_distance in extended regime: compute_mil uses interpolation"""
        p = self.spg
        tilt = 10.0
        d_input = 800.0  # extended regime
        candidate_mil = p.compute_mil(d_input) - tilt
        d_verify = p.inverse_mil(candidate_mil + tilt)
        self.assertAlmostEqual(d_verify, d_input, places=0)

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

    def test_spg_has_extended_range(self):
        """USA SPG has extended range table, STD does not"""
        self.assertEqual(len(self.spg.extended_range), 9)
        self.assertEqual(len(self.std.extended_range), 0)

    def test_spg_sector_layers(self):
        """SPG sector: inner at 600m, outer dynamic with tilt, max range at 915m"""
        # inner: always 600m
        self.assertEqual(self.spg.max_distance, 915.0)
        # with tilt=0: dynamic max = inverse_mil(466) = 732
        dyn_max_0 = self.spg.inverse_mil(min(466 + 0, 766))
        self.assertAlmostEqual(dyn_max_0, 732.0, places=0)
        # with tilt=300: dynamic max = inverse_mil(766) = 915
        dyn_max_300 = self.spg.inverse_mil(min(466 + 300, 766))
        self.assertEqual(dyn_max_300, 915.0)
        # default mil_flat should be 0
        self.assertEqual(USA_SPG.compute_mil(200.0), 100.0)  # standard formula works


if __name__ == "__main__":
    unittest.main()
