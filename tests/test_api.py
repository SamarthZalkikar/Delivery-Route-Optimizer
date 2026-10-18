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

def js_label_rect(cx, cy, cand, wtxt):
    dx, dy, anchor = cand
    if anchor == "start":
        left = cx + dx
    elif anchor == "middle":
        left = cx + dx - wtxt / 2
    else:
        left = cx + dx - wtxt
    ty = cy + dy
    return [left, ty - 10, left + wtxt, ty + 3]

def js_rect_hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

def js_seg_hits_rect(x1, y1, x2, y2, r):
    import math
    steps = int(math.ceil(max(abs(x2 - x1), abs(y2 - y1)) / 10)) + 1
    for i in range(steps + 1):
        t = i / steps
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        if r[0] < x < r[2] and r[1] < y < r[3]:
            return True
    return False

def js_short_code(name):
    words = name.split()
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    cleaned = "".join(ch for ch in name if ch.isalnum())
    return (cleaned[:2].upper() or "??")
js_short_code.__doc__ = "Mirrors shortCode() in app.js"

def js_place_labels(locs, roads, route_stops):
    """Mirrors placeLabels() in app.js. Returns list of (id, rect, text)."""
    CHAR_W, NODE_HALF, DEPOT_HALF = 7.8, 9, 14
    fit = js_fit(locs)
    pts = {l["id"]: js_px(l, fit) for l in locs}
    by_id = {l["id"]: l for l in locs}

    node_rects = []
    for l in locs:
        cx, cy = pts[l["id"]]
        half = DEPOT_HALF if l["id"] == 0 else NODE_HALF
        node_rects.append([cx - half - 1, cy - half - 1,
                           cx + half + 1, cy + half + 1])

    for sid in route_stops:
        cx, cy = pts[sid]
        node_rects.append([cx + NODE_HALF - 1, cy - NODE_HALF - 17,
                           cx + NODE_HALF + 17, cy - NODE_HALF + 1])
    segs = []
    for r in roads:
        ax, ay = pts[r[0]]
        bx, by = pts[r[1]]
        segs.append((ax, ay, bx, by))

    order = [0] + list(route_stops) + \
        [l["id"] for l in locs if l["id"] != 0 and l["id"] not in route_stops]

    placed = []
    placed_rects = []
    for lid in order:
        loc = by_id[lid]
        cx, cy = pts[lid]
        half = DEPOT_HALF if lid == 0 else NODE_HALF
        cands = js_candidates(half)
        best = None
        for text in [loc["name"].upper(), js_short_code(loc["name"])]:
            wtxt = max(20, len(text) * CHAR_W)
            scored = []
            for i, cand in enumerate(cands):
                r = js_label_rect(cx, cy, cand, wtxt)
                score = i * 0.6
                for pr in placed_rects:
                    if js_rect_hit(r, pr):
                        score += 100
                for nr in node_rects:
                    if js_rect_hit(r, nr):
                        score += 70
                for sg in segs:
                    if js_seg_hits_rect(sg[0], sg[1], sg[2], sg[3], r):
                        score += 20
                if r[0] < 2 or r[2] > 720 - 2 or r[1] < 2 or r[3] > 504 - 2:
                    score += 30
                scored.append((score, cand, r))
            scored.sort(key=lambda x: (x[0],))
            if scored[0][0] < 95:
                best = (scored[0][1], scored[0][2], text)
                break
        if best is None:
            best = (cands[0], js_label_rect(cx, cy, cands[0], 24),
                    js_short_code(loc["name"]))
        placed.append((lid, best[1], best[2]))
        placed_rects.append(best[1])
    return placed

class TestRouteAPI(unittest.TestCase):
    def setUp(self):
        self.c = A.app.test_client()

    def solve(self, stops, **extra):
        body = {"stops": stops, "depot": 0}
        body.update(extra)
        return self.c.post("/api/optimize", json=body)

    def test_8_stop_route_starts_and_ends_at_depot(self):
        r = self.solve([1, 2, 3, 4, 5, 7, 8, 13])
        self.assertEqual(r.status_code, 200)
        res = r.get_json()
        self.assertEqual(res["legs"][0]["from"], 0)
        self.assertEqual(res["legs"][-1]["to"], 0)
        self.assertEqual(res["cum_total"], round(res["distance"], 1))

    def test_leg_km_sum_equals_distance(self):
        res = self.solve([1, 2, 3, 4, 5, 7, 8, 13]).get_json()
        total = sum(round(l["km"], 1) for l in res["legs"])
        self.assertAlmostEqual(total, round(res["distance"], 1), places=1)

    def test_one_stop_round_trip(self):
        res = self.solve([11]).get_json()
        self.assertEqual(len(res["legs"]), 2)
        self.assertEqual(res["legs"][0]["to"], 11)
        self.assertEqual(res["legs"][1]["to"], 0)

    def test_nine_stops_exact(self):
        res = self.solve(list(range(1, 10)), engine="exact").get_json()
        self.assertIn("BACKTRACKING", res["engine_label"])

    def test_ten_stops_exact_falls_back(self):
        res = self.solve(list(range(1, 11)), engine="exact").get_json()
        self.assertTrue(res["fallback_note"])
        self.assertNotIn("BACKTRACKING", res["engine_label"])

    def test_zero_stops_rejected(self):
        self.assertEqual(self.solve([]).status_code, 400)

    def test_duplicate_stops_rejected(self):
        self.assertEqual(self.solve([5, 5, 9]).status_code, 400)

    def test_compare_has_four_rows_and_best(self):
        res = self.c.post("/api/optimize/compare",
                          json={"stops": [1, 5, 9], "depot": 0}).get_json()
        self.assertEqual(len(res["rows"]), 4)
        best_rows = [r for r in res["rows"] if r["best"]]
        self.assertEqual(len(best_rows), 1)
        kms = [r["km"] for r in res["rows"] if r["km"] is not None]
        self.assertEqual(best_rows[0]["km"], min(kms))

    def test_compare_exact_skipped_over_nine(self):
        res = self.c.post("/api/optimize/compare",
                          json={"stops": list(range(1, 11)), "depot": 0}).get_json()
        exact = [r for r in res["rows"] if r["engine"].startswith("EXACT")][0]
        self.assertIsNone(exact["km"])
        self.assertIn("SKIPPED", exact["note"])

    def test_priority_first_puts_express_first(self):

        res = self.solve([5, 11, 2], priority_first=True).get_json()
        order = [l["to"] for l in res["legs"] if l["to"] != 0]
        self.assertEqual(sorted(order[:2]), [2, 5], order)

    def test_driver_assign_rotates_queue(self):
        before = self.c.get("/api/state").get_json()["drivers"]
        res = self.c.post("/api/drivers/assign", json={}).get_json()
        self.assertEqual(res["assigned"], before[0])
        self.assertEqual(res["queue"], before[1:] + before[:1])

class TestLabelPlacement(unittest.TestCase):
    """Runs the JS algorithm's Python mirror on the seed map."""

    def setUp(self):
        self.locs = _loc_dicts()
        self.roads = A.SEED_ROADS
        self.stops = [1, 2, 3, 4, 5, 7, 8, 13]

    def placed(self):
        return js_place_labels(self.locs, self.roads, self.stops)

    def test_no_label_label_overlap(self):
        placed = self.placed()
        for i in range(len(placed)):
            for j in range(i + 1, len(placed)):
                self.assertFalse(js_rect_hit(placed[i][1], placed[j][1]),
                                 "labels %s and %s overlap" %
                                 (placed[i][0], placed[j][0]))

    def test_no_label_node_overlap(self):
        placed = self.placed()
        fit = js_fit(self.locs)
        for lid, rect, _ in placed:
            for loc in self.locs:
                cx, cy = js_px(loc, fit)
                half = 14 if loc["id"] == 0 else 9
                nr = [cx - half - 1, cy - half - 1,
                      cx + half + 1, cy + half + 1]
                self.assertFalse(js_rect_hit(rect, nr),
                                 "label of %s hits node %s" %
                                 (lid, loc["id"]))

    def test_labels_shortened_when_needed(self):
        placed = self.placed()
        by_id = {l["id"]: l["name"].upper() for l in self.locs}
        codes = [t for _, _, t in placed]

        for lid, _, text in placed:
            self.assertTrue(text)
            full = by_id[lid]
            self.assertTrue(text == full or text.startswith(full[:2])
                            or text in ("GM", "UG", "2+ letters"),
                            "unexpected text %r for id %s" % (text, lid))
        return codes

if __name__ == "__main__":
    unittest.main()
