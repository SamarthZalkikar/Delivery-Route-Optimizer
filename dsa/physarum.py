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

class PhysarumNetwork:
    """Edge-array model over local node indices 0..n-1.

    edges: [[u, v, km], ...] with NO duplicate (u, v) pairs (duplicates are
    merged on init, keeping the shorter length). All state lives in plain
    lists -- there is no dict/set/heap/sort inside the hot loop."""

    def __init__(self, n, edges):

        clean = []
        for e in edges:
            u, v, w = e[0], e[1], float(e[2])
            if u == v:
                continue
            if u > v:
                u, v = v, u
            hit = -1
            for k in range(len(clean)):
                if clean[k][0] == u and clean[k][1] == v:
                    hit = k
                    break
            if hit >= 0:
                if w < clean[hit][2]:
                    clean[hit][2] = w
            else:
                clean.append([u, v, w])
        self.n = n
        self.edges = clean
        self.L = [e[2] for e in clean]
        self.D = [1.0] * len(clean)

        self.nbr = [[] for _ in range(n)]
        self.nbr_e = [[] for _ in range(n)]
        for idx in range(len(clean)):
            u, v = clean[idx][0], clean[idx][1]
            self.nbr[u].append(v)
            self.nbr_e[u].append(idx)
            self.nbr[v].append(u)
            self.nbr_e[v].append(idx)

    def _pressures(self, src, dst, I0, x0):
        """Solve the SPD pressure system; returns full-length pressure list.

        Rows: one variable per non-sink node. Sink row deleted; the -D/L
        column term cancels because p_sink is pinned to 0."""
        n = self.n
        var_of = [-1] * n
        node_of = []
        vi = 0
        for i in range(n):
            if i != dst:
                var_of[i] = vi
                node_of.append(i)
                vi += 1
        m = vi
        b = [0.0] * m
        if src != dst:
            b[var_of[src]] = float(I0)
        conds = [self.D[e] / self.L[e] for e in range(len(self.D))]

        def matvec(pv):
            q = [0.0] * m
            for k in range(m):
                nid = node_of[k]
                pk = pv[k]
                acc = 0.0
                for t in range(len(self.nbr[nid])):
                    j = self.nbr[nid][t]
                    e = self.nbr_e[nid][t]
                    pj = pv[var_of[j]] if var_of[j] >= 0 else 0.0
                    acc += conds[e] * (pk - pj)
                q[k] = acc
            return q

        sol, _cgits = cg_solve(matvec, b, m, tol=1e-8, max_it=200,
                               x0=[x0[node_of[k]] for k in range(m)]
                               if x0 is not None else None)

        pf = [0.0] * n
        for k in range(m):
            pf[node_of[k]] = sol[k]
        return pf, var_of, conds
