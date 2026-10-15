"""
dsa/geo.py -- geographic helpers for the real-map / schematic map pair.

Everything is hand-written on top of `math` (no numpy). The haversine
formula gives the great-circle distance between two (lat, lng) points on a
sphere, using Earth's mean radius R = 6371.0 km.

haversine(lat1, lng1, lat2, lng2) in km:
    a  = sin^2( dlat/2 ) + cos(lat1) * cos(lat2) * sin^2( dlng/2 )
    c  = 2 * atan2( sqrt(a), sqrt(1 - a) )       # central angle
    km = R * c

Complexity: O(1) per call, pure float ops. Symmetric by construction
(dlat/dlng squared, cos of both lats multiply).
"""

import math

EARTH_R_KM = 6371.0

def haversine(lat1, lng1, lat2, lng2):
    """Great-circle distance in km on the mean-radius sphere."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = (math.sin(dp / 2.0) * math.sin(dp / 2.0) +
         math.cos(p1) * math.cos(p2) *
         math.sin(dl / 2.0) * math.sin(dl / 2.0))

    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_R_KM * c
