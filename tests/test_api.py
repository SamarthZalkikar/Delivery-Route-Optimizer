"""API-level checks (Task D) + a Python mirror of the JS label placement.

The label test mirrors static/app.js (placeLabels) exactly -- same constants,
same candidate list, same scoring -- so the display guarantee "no label
overlaps another label or a node square" is enforced offline for the seed map.
"""
import unittest

import app as A

def _loc_dicts():
    return [{"id": i, "name": t[0], "x": t[1], "y": t[2]}
            for i, t in enumerate(A.SEED_LOCATIONS)]

def js_fit(locs):
    """Mirrors computeFit() in app.js."""
    xs = [l["x"] for l in locs]
    ys = [l["y"] for l in locs]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w = max(1, maxx - minx)
    h = max(1, maxy - miny)
    s = min((720 - 96) / w, (504 - 96) / h)
    ox = (720 - w * s) / 2 - minx * s
    oy = (504 - h * s) / 2 - miny * s
    return s, ox, oy

def js_px(loc, fit):
    s, ox, oy = fit
    return (ox + loc["x"] * s, oy + loc["y"] * s)

def js_candidates(half):
    return [
        (half + 8, 4, "start"),
        (half + 8, -(half + 2), "start"),
        (0, -(half + 11), "middle"),
        (half + 8, half + 17, "start"),
        (0, half + 18, "middle"),
        (-(half + 8), 4, "end"),
        (-(half + 8), -(half + 2), "end"),
        (-(half + 8), half + 17, "end"),
    ]
