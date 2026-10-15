"""
dsa/optimizer.py -- Delivery route optimization.

Two engines behind /api/optimize:
  * EXACT   : backtracking TSP with an EXPLICIT DynStack (<= 9 stops) + pruning
  * HEURISTIC: nearest neighbour construction + 2-opt improvement (any n)
Cost matrix = shortest ROAD distances (Dijkstra) so the drawn route follows
real streets, not straight lines.

Complexities:
  exact    O(n! ) worst, massively cut by branch & bound (n <= 9 enforced)
  heuristic O(n^2) NN + O(n^2) per 2-opt pass, ~optimal on small city maps
"""

import time

from dsa.linear import DynStack
