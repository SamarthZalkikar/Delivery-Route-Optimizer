"""Tests for dsa/geo.py -- haversine + schematic/grid <-> lat/lng mapping."""

import unittest

from config import CITY_CENTER, DEG_LAT_PER_UNIT, DEG_LNG_PER_UNIT
from dsa.geo import (haversine, latlng_to_xy, xy_to_latlng, valid_latlng,
                     near_center)

class TestHaversine(unittest.TestCase):

    def test_known_distance_within_1pct(self):

        km = haversine(28.6139, 77.2090, 19.0760, 72.8777)
        self.assertGreater(km, 1000)
        self.assertLess(km, 1300)
        self.assertLess(abs(km - 1150) / 1150, 0.02)

    def test_symmetry(self):
        km1 = haversine(21.1458, 79.0882, 21.20, 79.12)
        km2 = haversine(21.20, 79.12, 21.1458, 79.0882)
        self.assertAlmostEqual(km1, km2, places=9)

    def test_zero_distance(self):
        self.assertEqual(haversine(21.1, 79.0, 21.1, 79.0), 0.0)

    def test_100m_grid_unit(self):
        """1 lat unit = 0.0009 deg ~= 100 m (7 decimals is honest)."""
        km = haversine(CITY_CENTER[0], CITY_CENTER[1],
                       CITY_CENTER[0] + DEG_LAT_PER_UNIT, CITY_CENTER[1])
        self.assertAlmostEqual(km, 0.1, places=2)

class TestGridMapping(unittest.TestCase):

    def test_roundtrip(self):
        for (x, y) in [(50, 50), (10, 90), (87, 3), (33, 66)]:
            lat, lng = xy_to_latlng(x, y, CITY_CENTER,
                                    DEG_LAT_PER_UNIT, DEG_LNG_PER_UNIT)
            x2, y2 = latlng_to_xy(lat, lng, CITY_CENTER,
                                  DEG_LAT_PER_UNIT, DEG_LNG_PER_UNIT)
            self.assertAlmostEqual(x, x2, places=6)
            self.assertAlmostEqual(y, y2, places=6)

    def test_center_is_50_50(self):
        x, y = latlng_to_xy(CITY_CENTER[0], CITY_CENTER[1], CITY_CENTER,
                            DEG_LAT_PER_UNIT, DEG_LNG_PER_UNIT)
        self.assertAlmostEqual(x, 50.0, places=9)
        self.assertAlmostEqual(y, 50.0, places=9)

    def test_y_grows_south(self):
        lat, _lng = xy_to_latlng(50, 60, CITY_CENTER,
                                 DEG_LAT_PER_UNIT, DEG_LNG_PER_UNIT)
        self.assertLess(lat, CITY_CENTER[0])

class TestValidation(unittest.TestCase):

    def test_valid_latlng(self):
        self.assertTrue(valid_latlng(21.14, 79.08))
        self.assertFalse(valid_latlng(95, 79.08))
        self.assertFalse(valid_latlng("21", 79.08))
        self.assertFalse(valid_latlng(True, 79.08))
        self.assertFalse(valid_latlng(None, None))

    def test_near_center(self):
        self.assertTrue(near_center(21.15, 79.09, CITY_CENTER))
        self.assertFalse(near_center(30.0, 79.09, CITY_CENTER))

if __name__ == "__main__":
    unittest.main()
