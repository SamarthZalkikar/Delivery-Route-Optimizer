"""
Delivery-Route-Optimizer -- Flask app + JSON API.

The Store class owns every DSA structure from dsa/ and is the single source of
state. All input is validated; errors come back as {"error": "..."} with a
proper 4xx code. dict/list literals are used ONLY to shape JSON responses.
"""

from flask import Flask, jsonify, render_template, request

import time
import random

from dsa.linear import DynStack, MinHeapPQ, CircularQueue, SortedListPQ
from dsa.linked import Polynomial, CircularLinkedList
from dsa.trees import AVLTree, BTree, BPlusTree
from dsa.trie import Trie
from dsa.hashing import hash_division, hash_mid_square, hash_folding, \
    HashTableChaining, HashTableOpen
from dsa.graph import Graph, dijkstra_all_pairs, bfs_order, dfs_order, \
    connected_components, prim_mst, kruskal_mst, path_via_prev, shortest_path
from dsa.physarum import PhysarumNetwork
from dsa.dsu import DSU
from dsa.sparse import SparseMatrix
from dsa.sorting import (benchmark_all, external_sort, merge_sort_orders,
                         linear_search, binary_search, merge_sort)
from dsa.optimizer import RouteOptimizer

app = Flask(__name__)

import config
from dsa.geo import (haversine, latlng_to_xy, xy_to_latlng,
                     valid_latlng, near_center)

SEED_LOCATIONS = [

    ["Central Depot", 50, 50],
    ["Gateway Mall", 20, 30],
    ["North Market", 65, 15],
    ["Riverside Park", 85, 30],
    ["Old Town Hall", 15, 65],
    ["Tech Park West", 75, 70],
    ["South Junction", 40, 85],
    ["University Gate", 90, 50],
    ["Harbour Docks", 70, 90],
    ["Station Square", 50, 30],
    ["Clifftop Retreat", 10, 20],
    ["Stadium Zone", 60, 60],
    ["Crystal Plaza", 35, 70],
    ["Airport City", 95, 85],
]

SEED_ROADS = [
    [0, 9], [0, 11], [0, 12], [0, 2],
    [1, 10], [1, 9], [1, 4],
    [2, 9], [2, 3],
    [3, 7],
    [4, 12], [4, 6],
    [5, 11], [5, 7], [5, 13],
    [6, 8], [6, 12],
    [7, 13],
    [8, 13],
    [11, 12],
]

SEED_ORDERS = [
    ["Ishita Rao", 2, 1, 4.5],
    ["Manav Patel", 3, 2, 12.0],
    ["Sara Khan", 5, 1, 2.0],
    ["Daniel Fernandes", 8, 3, 20.0],
    ["Priya Nair", 11, 2, 6.5],
    ["Arjun Mehta", 9, 1, 3.2],
    ["Fatima Sheikh", 4, 3, 15.0],
    ["Rahul Bose", 7, 2, 8.0],
    ["Meera Iyer", 10, 3, 11.0],
    ["John Cardoza", 13, 1, 5.0],
]

class Store:
    """Application state container.

    Seeded once on import; RESTless endpoints mutate it. Every structure from
    the syllabus is actively used here (see README matrix)."""

    def __init__(self):
        self.undo = DynStack()
        self.shape_cache = HashTableChaining()
        self._last_shape_ts = 0.0
        self._build_graph()
        self._seed_orders()
        self._seed_labs()

    def _xy_latlng(self, x, y):
        """Schematic grid (x,y) -> (lat, lng) using config scales."""
        return xy_to_latlng(x, y, config.CITY_CENTER,
                            config.DEG_LAT_PER_UNIT, config.DEG_LNG_PER_UNIT)

    def _road_weight(self, lat1, lng1, lat2, lng2):
        """Straight-line haversine x ROAD_FACTOR, rounded to 0.1 km."""
        return round(haversine(lat1, lng1, lat2, lng2) * config.ROAD_FACTOR, 1)

    def _build_graph(self):
        self.locations = []
        for lid, (name, x, y) in enumerate(SEED_LOCATIONS):
            lat, lng = self._xy_latlng(x, y)
            loc = {"id": lid, "name": name, "x": x, "y": y,
                   "lat": round(lat, 5), "lng": round(lng, 5)}
            self.locations.append(loc)
        self.g = Graph(len(self.locations))
        self.roads = []
        for u, v in SEED_ROADS:
            fu = self.locations[u]
            fv = self.locations[v]
            w = self._road_weight(fu["lat"], fu["lng"], fv["lat"], fv["lng"])
            self.g.add_edge(u, v, w)
            self.roads.append({"u": u, "v": v, "w": w})
        self._rebuild_matrices()

    def _rebuild_matrices(self):
        self.dist, self.prevmap = dijkstra_all_pairs(self.g)
        self.optimizer = RouteOptimizer(self.dist)
        from dsa.physarum import PhysarumNetwork
        self.pnet = PhysarumNetwork(self.g.n, self.g.edges)
        self.leg_cache = HashTableChaining(size=97)

        road_matrix = [[0.0] * self.g.n for _ in range(self.g.n)]
        for u, v, w in self.g.edges:
            road_matrix[u][v] = w
        self.sparse = SparseMatrix.from_dense(road_matrix)
        comps, _labels = connected_components(self.g)
        self.components = comps
