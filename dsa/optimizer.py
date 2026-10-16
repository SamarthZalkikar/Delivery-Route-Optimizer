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

    def __init__(self, dist_matrix):
        self.dm = dist_matrix
        self.n = len(dist_matrix)
        self.min_edge = self._min_edge()

    def _min_edge(self):
        """Cheapest single hop anywhere in the matrix = lower-bound gadget
        for the prune test (cost + remaining * min_edge >= best)."""
        m = float("inf")
        for i in range(self.n):
            for j in range(self.n):
                if i != j and self.dm[i][j] < m:
                    m = self.dm[i][j]
        return 0.0 if m == float("inf") else m

    def optimize_exact(self, stops, depot, time_limit=None):
        """Branch & bound DFS with an EXPLICIT DynStack; frames hold
        [path, cost, visited=[T/F]*k].

        Prune rules:
          1) partial cost >= best
          2) cost + remaining*min_edge >= best  (min-edge lower bound)
        Candidates are tried NEAREST-FIRST so good incumbents appear early.

        Returns (best_order, best_cost, steps). Raises ValueError > 9 stops."""
        k = len(stops)
        if k == 0:
            return [], 0.0, 0
        if k > 9:
            raise ValueError("exact mode supports at most 9 stops")
        best = {"cost": float("inf"), "order": None}
        steps = 0
        pruned = 0
        t0 = time.perf_counter()

        stack = DynStack()

        for i, st in enumerate(stops):
            visited = [False] * k
            visited[i] = True
            stack.push([[st], self.dm[depot][st], visited])

        while not stack.is_empty():
            if time_limit and (time.perf_counter() - t0) > time_limit:
                break
            path, cost, visited = stack.pop()
            steps += 1
            if cost >= best["cost"]:
                pruned += 1
                continue
            if len(path) == k:
                total = cost + self.dm[path[-1]][depot]
                if total < best["cost"]:
                    best["cost"] = total
                    best["order"] = list(path)
                continue
            remaining = k - len(path)
            if cost + remaining * self.min_edge >= best["cost"]:
                pruned += 1
                continue
            cur = path[-1]

            cand = []
            for j, st in enumerate(stops):
                if not visited[j]:
                    cand.append([self.dm[cur][st], j, st])
            insertion_sort(cand)
            while cand:
                dc, j, st = cand.pop()
                nvis = list(visited)
                nvis[j] = True
                stack.push([path + [st], cost + dc, nvis])
        self.last_pruned = pruned
        return best["order"], best["cost"], steps
