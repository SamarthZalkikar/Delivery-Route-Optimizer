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

def insertion_sort(items, key=lambda x: x[0]):
    """Plain insertion sort for candidate ordering (no list.sort used). O(n^2)."""
    for i in range(1, len(items)):
        cur = items[i]
        j = i - 1
        while j >= 0 and key(items[j]) > key(cur):
            items[j + 1] = items[j]
            j -= 1
        items[j + 1] = cur
    return items

class RouteOptimizer:
    """TSP-style route planner over a symmetric distance matrix.

    Cost matrix `dm` is the Dijkstra road-distance matrix (n x n plain array).
    Stops are location indices; the depot is one of those indices.
    """
