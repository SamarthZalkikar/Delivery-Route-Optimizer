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
