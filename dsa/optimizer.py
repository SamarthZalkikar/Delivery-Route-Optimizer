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

    def nearest_neighbour(self, stops, depot):
        """Greedy: always hop to the nearest unvisited stop. O(k^2)."""
        if not stops:
            return [], 0.0, 0
        unvis = list(stops)
        path, cost, steps = [], 0.0, 0
        cur = depot
        while unvis:
            best_j, best_w = 0, float("inf")
            for j in range(len(unvis)):
                steps += 1
                w = self.dm[cur][unvis[j]]
                if w < best_w:
                    best_w, best_j = w, j
            nxt = unvis[best_j]
            unvis[best_j] = unvis[-1]
            unvis.pop()
            path.append(nxt)
            cost += self.dm[cur][nxt]
            cur = nxt
        cost += self.dm[path[-1]][depot] if path else 0.0
        return path, cost, steps

    def tour_cost(self, order, depot):
        """Closed-tour cost depot -> stops -> depot, or 0 for an empty order."""
        if not order:
            return 0.0
        c = self.dm[depot][order[0]]
        for i in range(1, len(order)):
            c += self.dm[order[i - 1]][order[i]]
        return c + self.dm[order[-1]][depot]

    def two_opt(self, order, depot):
        """2-opt improvement: repeatedly reverse two-cut segments whenever the
        reversal shrinks the closed tour. O(k^2) per pass, a few passes."""
        if len(order) < 3:
            return order, self.tour_cost(order, depot), 0
        steps = 0
        improved = True
        while improved:
            improved = False
            for i in range(len(order) - 1):
                for j in range(i + 1, len(order)):
                    steps += 1
                    a = depot if i == 0 else order[i - 1]
                    b = order[i]
                    c = order[j]
                    d = depot if j == len(order) - 1 else order[j + 1]
                    delta = (self.dm[a][c] + self.dm[b][d]) - (self.dm[a][b] + self.dm[c][d])
                    if delta < -1e-9:
                        order[i:j + 1] = order[i:j + 1][::-1]
                        improved = True
        return order, self.tour_cost(order, depot), steps

    def optimize_heuristic(self, stops, depot):
        """NN construction then 2-opt polishing. Returns (order, cost, steps)."""
        path, cost, s1 = self.nearest_neighbour(stops, depot)
        path2, cost2, s2 = self.two_opt(list(path), depot)
        return path2, cost2, s1 + s2

    def optimize(self, stops, depot, mode="auto"):
        """Dispatcher used by the API. mode: exact | nn | nn2opt | heuristic | auto.
        auto picks exact for <= 9 stops, nn2opt beyond.
        The chosen engine label + complexity notes ride along in the result."""
        engine = mode.lower()
        if engine == "auto":
            engine = "exact" if len(stops) <= 9 else "nn2opt"
        elif engine == "heuristic":
            engine = "nn2opt"
        if engine not in ("exact", "nn", "nn2opt"):
            raise ValueError("mode must be exact | nn | nn2opt | heuristic | auto")
        self.last_pruned = 0
        t0 = time.perf_counter()
        if engine == "exact":
            order, cost, steps = self.optimize_exact(stops, depot)
            algo = "Backtracking TSP (explicit stack + branch & bound)"
            complexity = "O(n!) with branch & bound pruning"
            pruned = self.last_pruned
        elif engine == "nn":
            order, cost, steps = self.nearest_neighbour(stops, depot)
            algo = "Nearest neighbour (greedy)"
            complexity = "O(n^2) construction, no improvement pass"
            pruned = 0
        else:
            order, cost, steps = self.optimize_heuristic(stops, depot)
            algo = "Nearest neighbour + 2-opt"
            complexity = "O(n^2) nearest neighbour + O(n^2) 2-opt per pass"
            pruned = 0
        elapsed = (time.perf_counter() - t0) * 1000.0
        return {
            "order": order,
            "cost": round(cost, 2),
            "steps": steps,
            "algorithm": algo,
            "complexity": complexity,
            "engine": engine,
            "mode": engine,
            "pruned": pruned,
            "ms": round(elapsed, 3),
        }
