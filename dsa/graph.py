"""
dsa/graph.py -- Unit-III graph algorithms over an ADJACENCY-LIST graph.

Used BY the app for:
  * BFS / DFS traversals            (Network tab, /api/traverse)
  * connected components            (DSU-backed)
  * Dijkstra shortest paths         (feeds the route optimizer's distance matrix)
  * Prim & Kruskal MSTs side by side
Design: node ids are ints 0..n-1, adjacency is a plain LIST OF LISTS
(neighbor lists), no dict/set inside the algorithms.
"""

from dsa.dsu import DSU
from dsa.linear import MinHeapPQ, ArrayDeque, DynStack

class Graph:
    """Undirected weighted graph, adjacency-list representation.

    Node ids are dense ints; adjacency[u] = list of (v, w) pairs -- a plain
    nested array, which keeps the viva story clean ("adjacency LIST").
    add_edge O(1); n_nodes O(1)."""
    __slots__ = ("n", "adjacency", "edges")

    def __init__(self, n=0):
        self.n = n
        self.adjacency = [[] for _ in range(n)]
        self.edges = []

    def add_node(self):
        """Grow adjacency by one row. O(1)."""
        self.adjacency.append([])
        nid = self.n
        self.n += 1
        return nid

    def has_edge(self, u, v):
        for e in self.adjacency[u]:
            if e[0] == v:
                return True
        return False

    def add_edge(self, u, v, w):
        """Undirected edge stored twice (u->v, v->u). O(2)."""
        if u is None or v is None:
            raise ValueError("edge endpoints must both exist")
        self.adjacency[u].append([v, w])
        self.adjacency[v].append([u, w])
        self.edges.append([u, v, w])

    def edges_sorted_by_weight(self):
        """Insertion-sort a copy of the edge list by weight (no list.sort).
        O(E^2) worst but E is small (city roads)."""
        out = [list(e) for e in self.edges]
        for i in range(1, len(out)):
            cur = out[i]
            j = i - 1
            while j >= 0 and out[j][2] > cur[2]:
                out[j + 1] = out[j]
                j -= 1
            out[j + 1] = cur
        return out

    def node_count(self):
        return self.n

    def edge_count(self):
        return len(self.edges)

def bfs_order(graph, start):
    """BFS with the project's own ArrayDeque fringe; O(V + E).
    Returns visit order + levels (depths)."""
    visited = [False] * graph.n
    order, levels = [], []
    q = ArrayDeque()
    visited[start] = True
    q.push_back(start)
    lvl = [0] * graph.n
    lvl[start] = 0
    while not q.is_empty():
        u = q.pop_front()
        order.append(u)
        levels.append(lvl[u])

        neigh = []
        for e in graph.adjacency[u]:
            neigh.append(e)
        for e in neigh:
            v = e[0]
            if not visited[v]:
                visited[v] = True
                lvl[v] = lvl[u] + 1
                q.push_back(v)
    return order, levels
