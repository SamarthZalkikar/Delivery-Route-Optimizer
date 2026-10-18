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
