"""
config.py -- single place for the physical-city constants.

Everything here is tunable; nothing else in the project hard-codes coordinates.
No API keys belong in this file (see README: why there is no Google Maps).
"""

CITY_CENTER = (21.1458, 79.0882)

GRID_KM = 10.0
DEG_LAT_PER_UNIT = 0.0009

DEG_LNG_PER_UNIT = 0.000963

ROAD_FACTOR = 1.25

OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
OSRM_TIMEOUT = 3.0
