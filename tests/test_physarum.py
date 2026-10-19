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
