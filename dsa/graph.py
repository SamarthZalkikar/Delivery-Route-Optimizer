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
