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
