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
