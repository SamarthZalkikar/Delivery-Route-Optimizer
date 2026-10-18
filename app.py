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

    def add_location(self, lat, lng, name, x=None):
        """Add a location, connect it to its k nearest neighbours using the
        project's own MinHeapPQ (k=3 for geo callers, 2 for legacy grid), then
        use Union-Find to prove the graph is still connected -- if not, bridge
        with the shortest connecting edge.

        Callers pass lat/lng (the map view). add_location_xy() is the legacy
        schematic-grid wrapper."""
        if len(self.locations) >= 50:
            return None, "at most 50 locations"
        if not (1 <= len(str(name).strip()) <= 40):
            return None, "name must be 1..40 characters"
        name = str(name).strip()
        if not valid_latlng(lat, lng):
            return None, "lat must be in [-90, 90] and lng in [-180, 180]"
        if not near_center(lat, lng, config.CITY_CENTER):
            return None, "location must be within ~35 km of the city center"
        gx, gy = latlng_to_xy(lat, lng, config.CITY_CENTER,
                              config.DEG_LAT_PER_UNIT, config.DEG_LNG_PER_UNIT)
        gx, gy = int(round(gx)), int(round(gy))
        for loc in self.locations:
            if loc["name"].strip().upper() == name.upper():
                return None, "a location named '%s' already exists" % name
            if abs(abs(loc["lat"]) - abs(lat)) < 1e-4 and \
               abs(abs(loc["lng"]) - abs(lng)) < 1e-4:
                return None, "a location already exists at this spot"
        lid = len(self.locations)
        self.locations.append({"id": lid, "name": name, "x": gx, "y": gy,
                               "lat": round(float(lat), 5),
                               "lng": round(float(lng), 5)})
        self.g.add_node()

        k = 3
        pq = MinHeapPQ()
        weights = self._road_weight
        for other in self.locations:
            if other["id"] == lid:
                continue
            pq.push(weights(other["lat"], other["lng"], float(lat), float(lng)),
                    other["id"])
        connected_edges = 0
        while not pq.is_empty() and connected_edges < k:
            w, oid = pq.pop_min()
            self.g.add_edge(lid, oid, round(float(w), 1))
            self.roads.append({"u": lid, "v": oid, "w": round(float(w), 1)})
            connected_edges += 1
        if connected_edges == 0:
            return None, "no other locations to connect to"

        dsu = DSU(len(self.locations))
        for u, v, _w in self.g.edges:
            dsu.union(u, v)
        if len(dsu.components()) != 1:
            best = None
            for u in range(len(self.locations)):
                for v in range(u + 1, len(self.locations)):
                    if dsu.find(u) != dsu.find(v):
                        wv = weights(self.locations[u]["lat"],
                                     self.locations[u]["lng"],
                                     self.locations[v]["lat"],
                                     self.locations[v]["lng"])
                        if best is None or wv < best[0]:
                            best = [wv, u, v]
            if best is None:
                return None, "nodes do not connect"
            wv, u, v = best
            self.g.add_edge(u, v, wv)
            self.roads.append({"u": u, "v": v, "w": wv})
            dsu.union(u, v)

        self.trie.insert(name)
        self._rebuild_matrices()
        return lid, None

    def add_location_xy(self, x, y, name):
        """Legacy schematic-grid wrapper (x,y in 0..100)."""
        lat, lng = self._xy_latlng(x, y)
        return self.add_location(lat, lng, name)

    def _seed_orders(self):
        self.orders = []
        self.next_number = 1001
        self.seq = 0
        self.avl = AVLTree()
        self.btree = BTree(t=3)
        self.bplus = BPlusTree(m=4)
        for cus, loc, prio, weight in SEED_ORDERS:
            self.create_order(cus, loc, prio, weight)
        self.drivers = CircularQueue(4)
        for dn in ["Driver-Dhruv", "Driver-Kavya", "Driver-Tenzin"]:
            self.drivers.enqueue(dn)
        self.deliveries = []

    def create_order(self, customer, location, priority, weight, replay=False):
        self.seq += 1
        number = self.next_number
        self.next_number += 1
        order = {
            "number": number,
            "id": "ORD-%d" % number,
            "customer": customer,
            "location": location,
            "priority": priority,
            "weight": weight,
            "status": "PENDING",
            "driver": None,
            "seq": self.seq,
        }
        self.orders.append(order)
        self.avl.insert(number, order)
        self.btree.insert(number, order)
        self.bplus.insert(number, order)
        if not replay:
            self.undo.push(["ADD", order["id"]])
        return order

    def remove_order(self, order_id):
        """Common tail of undo(ADD): drop from list + all three indexes."""
        num = int(order_id.split("-")[1])
        for i in range(len(self.orders)):
            if self.orders[i]["id"] == order_id:
                del self.orders[i]
                break
        self.avl.delete(num)
        self.btree.delete(num)
        self.bplus.insert(num, None)
        return num
