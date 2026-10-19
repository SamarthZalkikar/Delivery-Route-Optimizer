"""Tests for the Physarum (slime mold) path finder -- bio-inspired heuristic
with Dijkstra as the exact reference. Uses hand-written structures only."""

import time
import unittest

from dsa.physarum import PhysarumNetwork, cg_solve

import app as A

def diamond_net():
    """Two routes src->dst: short 3+3, long 5+5."""
    return PhysarumNetwork(4, [[0, 1, 3], [1, 3, 3], [0, 2, 5], [2, 3, 5]])

class TestCGSolver(unittest.TestCase):
    """The Conjugate Gradient on a small known SPD system."""

    def test_known_2x2(self):

        def mv(v):
            return [4 * v[0] + 1 * v[1], 1 * v[0] + 3 * v[1]]

        x, its = cg_solve(mv, [1.0, 2.0], 2, tol=1e-8, max_it=200)
        self.assertAlmostEqual(x[0], 1.0 / 11.0, places=6)
        self.assertAlmostEqual(x[1], 7.0 / 11.0, places=6)
        self.assertLessEqual(its, 10)

    def test_identity(self):
        x, _ = cg_solve(lambda v: list(v), [3.0, -2.0, 5.0], 3)
        for got, want in zip(x, [3.0, -2.0, 5.0]):
            self.assertAlmostEqual(got, want, places=8)

class TestPhysarumCore(unittest.TestCase):

    def test_diamond_short_tube_dominates(self):
        """Tiny diamond: the short path's D ends > 100x the long path's."""
        net = diamond_net()
        res = net.solve(0, 3)
        self.assertEqual(res["path"], [0, 1, 3])
        self.assertAlmostEqual(res["km"], 6.0, places=6)
        self.assertGreater(net.D[0], 100 * net.D[2])
        self.assertGreater(net.D[1], 100 * net.D[3])

    def test_source_equals_sink(self):
        net = diamond_net()
        res = net.solve(2, 2)
        self.assertEqual(res["path"], [2])
        self.assertEqual(res["km"], 0.0)
        self.assertTrue(res["converged"])

    def test_adjacent_nodes(self):
        net = diamond_net()
        res = net.solve(0, 1)
        self.assertEqual(res["path"], [0, 1])
        self.assertAlmostEqual(res["km"], 3.0, places=6)

    def test_disconnected_graph_fails_cleanly(self):
        net = PhysarumNetwork(6, [[0, 1, 2], [1, 2, 2],
                                  [3, 4, 2], [4, 5, 2]])
        res = net.solve(0, 5)
        self.assertIsNone(res["path"])

    def test_frames_never_exceed_120(self):
        net = PhysarumNetwork(A.STORE.g.n, A.STORE.g.edges)
        res = net.solve(0, 7, max_iter=500)
        self.assertLessEqual(len(res["frames"]), 120)

    def test_single_pair_under_300ms(self):
        net = PhysarumNetwork(A.STORE.g.n, A.STORE.g.edges)
        t0 = time.perf_counter()
        res = net.solve(0, 8)
        ms = (time.perf_counter() - t0) * 1000
        self.assertGreater(res["iterations"], 0)
        self.assertLess(ms, 300.0, "single solve should stay << 300 ms")

    def test_duplicate_edges_merged(self):
        net = PhysarumNetwork(3, [[0, 1, 4], [1, 0, 3], [1, 2, 2]])
        self.assertEqual(len(net.edges), 2)
        self.assertEqual(net.L, [3.0, 2.0])

class TestPhysarumAgainstDijkstra(unittest.TestCase):
    """20 deterministic stop pairs: slime km == dijkstra km within 1%."""

    def test_twenty_pairs_city_graph(self):
        net = PhysarumNetwork(A.STORE.g.n, A.STORE.g.edges)
        state = [42]

        def lcg():
            state[0] = (1103515245 * state[0] + 12345) % 2147483648
            return state[0]

        n = A.STORE.g.n
        matched = 0
        for _t in range(20):
            a = lcg() % n
            b = lcg() % n
            while b == a:
                b = (b + 1) % n
            res = net.solve(a, b)
            dk = A.STORE.dist[a][b]
            if res["path"] is not None:
                diff = abs(res["km"] - dk) / dk * 100
                self.assertLessEqual(diff, 1.0,
                                     "pair %d->%d missed the 1%% bar" % (a, b))
                matched += 1
        self.assertGreaterEqual(matched, 18,
                                "tube walk should succeed on nearly all pairs")

class TestPhysarumAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.c = A.app.test_client()

    def test_physarum_endpoint_shape(self):
        r = self.c.post("/api/physarum", json={"source": 0, "sink": 5})
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        for key in ("ok", "source", "sink", "path", "km", "physarum_km",
                    "dijkstra_km", "dijkstra_path", "iterations", "converged",
                    "within_1pct", "frames", "edges",
                    "physarum_ms", "dijkstra_ms"):
            self.assertIn(key, j)
        self.assertEqual(j["source"], 0)
        self.assertEqual(j["sink"], 5)
        self.assertTrue(j["within_1pct"])

        self.assertLessEqual(len(j["frames"]), 120)
        self.assertEqual(len(j["edges"]), len(j["frames"][0][1]))

    def test_physarum_defaults_kick_in(self):
        r = self.c.post("/api/physarum", json={"source": 1, "sink": 9})
        self.assertEqual(r.status_code, 200)

    def test_source_equals_sink_400(self):
        r = self.c.post("/api/physarum", json={"source": 3, "sink": 3})
        self.assertEqual(r.status_code, 400)
        self.assertIn("different", r.get_json()["error"])

    def test_bad_parameters_400(self):
        for bad in ({"g": 9}, {"mu": -1}, {"dt": 5}, {"I0": 0}):
            body = {"source": 0, "sink": 4}
            body.update(bad)
            r = self.c.post("/api/physarum", json=body)
            self.assertEqual(r.status_code, 400, bad)
        r = self.c.post("/api/physarum", json={"source": 999, "sink": 4})
        self.assertEqual(r.status_code, 400)

    def test_physarum_engine_on_optimize(self):
        r = self.c.post("/api/optimize",
                        json={"depot": 0, "stops": [1, 2, 3, 4],
                              "engine": "physarum"})
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertIn("PHYSARUM LEGS", j["engine_label"])
        self.assertIn("physarum", j)
        self.assertTrue(j["physarum"]["pair_ms"] >= 0)
        self.assertLessEqual(j["physarum"]["worst_diff_pct"], 1.0)

        self.assertGreaterEqual(len(j["geometry"]), 5)

    def test_physarum_engine_cap(self):
        r = self.c.post("/api/optimize",
                        json={"depot": 0, "stops": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                              "engine": "physarum"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("capped", r.get_json()["error"])

    def test_growth_endpoint(self):
        r = self.c.post("/api/physarum/growth",
                        json={"stops": [1, 2, 3, 4], "pairs": 8, "iters": 6,
                              "seed": 7})
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertIn("SLIME", j["verdict"])
        self.assertIn("MST", j["verdict"])
        self.assertEqual(len(j["frames"]), 8)
        self.assertTrue(j["total_length"] <= j["full_total"])

        r2 = self.c.post("/api/physarum/growth",
                         json={"stops": [1, 2, 3, 4], "pairs": 8, "iters": 6,
                               "seed": 7})
        self.assertEqual(j["pairs_used"], r2.get_json()["pairs_used"])

    def test_growth_needs_stops(self):
        r = self.c.post("/api/physarum/growth", json={"stops": [1]})
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/physarum/growth", json={"stops": [1, 2],
                                                      "seed": -3})
        self.assertEqual(r.status_code, 400)

class TestPhysarumFrames(unittest.TestCase):
    """Frame contract for the redesigned Slime Lab: at most 90 frames,
    LOG-SPACED over the real iteration numbers (dense early, sparse late),
    always covering iteration 0 AND the final iteration, plus a 60-iteration
    visualisation floor so the tubes visibly settle."""

    def test_frames_capped_at_90(self):
        net = PhysarumNetwork(A.STORE.g.n, A.STORE.g.edges)
        res = net.solve(0, 7, max_iter=500)
        self.assertLessEqual(len(res["frames"]), 90)

    def test_frames_log_spaced_with_real_iterations(self):
        net = PhysarumNetwork(A.STORE.g.n, A.STORE.g.edges)
        res = net.solve(0, 7, max_iter=500)
        iters = [f[0] for f in res["frames"]]

        self.assertEqual(iters[0], 0)
        self.assertEqual(iters[-1], res["iterations"])
        self.assertEqual(len(iters), len(set(iters)))
        self.assertTrue(all(b > a for a, b in zip(iters, iters[1:])))

        gaps = [b - a for a, b in zip(iters, iters[1:])]
        self.assertTrue(all(b >= a for a, b in zip(gaps, gaps[1:])))
        self.assertEqual(gaps[0], 1)

    def test_min_iterations_floor(self):
        """Converged early still runs >= 60 iterations (frames settle);
        converged_at is reported separately and honestly."""
        net = PhysarumNetwork(A.STORE.g.n, A.STORE.g.edges)
        res = net.solve(0, 8, max_iter=500)
        self.assertGreaterEqual(res["iterations"], 60)
        self.assertTrue(res["converged"])
        self.assertIsNotNone(res["converged_at"])
        self.assertLessEqual(res["converged_at"], res["iterations"])
        self.assertIsNotNone(res["path"])

    def test_five_pairs_iteration_counts(self):
        """Stop criterion is not loose: five sample src/sink pairs all run
        a real (>= 60 iteration) solve and converge with a reported mark."""
        counts = []
        for src, dst in ((0, 5), (1, 9), (2, 11), (4, 13), (6, 10)):
            net = PhysarumNetwork(A.STORE.g.n, A.STORE.g.edges)
            res = net.solve(src, dst, max_iter=500)
            counts.append((src, dst, res["iterations"], res["converged_at"]))
            self.assertGreaterEqual(res["iterations"], 60, (src, dst))
            self.assertTrue(res["converged"], (src, dst))
        print("iteration counts (src, dst, iters, converged_at): %s" % counts)

    def test_endpoint_always_reports_both_engines(self):
        """The path-finder response always carries the Physarum result AND
        its Dijkstra twin (km, ms, path) plus the frame contract fields."""
        c = A.app.test_client()
        for src, dst in ((0, 5), (3, 12)):
            r = c.post("/api/physarum", json={"source": src, "sink": dst})
            self.assertEqual(r.status_code, 200)
            j = r.get_json()
            for key in ("physarum_km", "physarum_ms", "dijkstra_km",
                        "dijkstra_ms", "dijkstra_path", "converged_at",
                        "frames"):
                self.assertIn(key, j, (src, dst, key))
            self.assertLessEqual(len(j["frames"]), 90)

if __name__ == "__main__":
    unittest.main()
