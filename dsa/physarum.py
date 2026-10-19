"""
dsa/physarum.py -- Physarum polycephalum tube dynamics (Tero et al. 2010),
adapted to a weighted undirected graph of city roads.

WARNING (viva note): this is a BIO-INSPIRED HEURISTIC. It *usually* finds the
shortest path, but Dijkstra is the EXACT reference and stays the default
everywhere in this project. Every Physarum solve returns its Dijkstra twin so
the UI can prove agreement.

The model, in plain text, per undirected edge (i, j) with length L_ij (km):
  p_i        node pressure; source gets inflow +I0, sink -I0, p_sink = 0.
  Q_ij       flux  = (D_ij / L_ij) * (p_i - p_j)      (sign gives direction)
  D_ij      += dt * ( |Q_ij|^g / (1 + |Q_ij|^g)  -  mu * D_ij )
             flow grows conductance, mu decays it; long unused roads starve.

Pressures come from a symmetric positive-definite system: for every non-sink
node i, sum_j (D_ij / L_ij) * (p_i - p_j) = inflow_i, with the sink pinned to
p = 0. Solved by a hand-written Conjugate Gradient over adjacency-aligned
O(E) matrix-vector products -- O(E) per CG step, no numpy.

Complexity: one adaptation loop over E edges is O(E); each outer iteration
costs O(cg_its * E + E), cg_its small for city graphs (typically < 40).
"""

import math
import time

def _dot(a, b):
    s = 0.0
    for i in range(len(a)):
        s += a[i] * b[i]
    return s

def cg_solve(matvec, b, m, tol=1e-8, max_it=200, x0=None):
    """Solve A x = b for SPD A via CG. A is given as a matvec function.

    Returns (x, its). x0 enables warm starts between Physarum iterations
    (pressures move slowly, so the same guess is nearly exact next round).
    O(E) per iteration when matvec streams the adjacency lists once."""
    x = [0.0] * m if x0 is None else list(x0)
    r = list(b)
    ax = matvec(x)
    for i in range(m):
        r[i] -= ax[i]
    p = list(r)
    rr = _dot(r, r)
    bnorm = math.sqrt(_dot(b, b)) or 1.0
    its = 0
    for _ in range(max_it):
        if math.sqrt(rr) <= tol * bnorm:
            break
        ap = matvec(p)
        pap = _dot(p, ap)
        if pap <= 1e-30:
            break
        alpha = rr / pap
        for i in range(m):
            x[i] += alpha * p[i]
            r[i] -= alpha * ap[i]
        rr_new = _dot(r, r)
        beta = rr_new / rr
        for i in range(m):
            p[i] = r[i] + beta * p[i]
        rr = rr_new
        its += 1
    return x, its
