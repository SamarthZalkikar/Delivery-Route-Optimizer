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

    def lookup_order(self, order_id):
        """GET /api/orders/<id> -- AVL search answers this in O(log n)."""
        try:
            num = int(order_id.split("-")[1])
        except (ValueError, IndexError):
            return None
        val, steps = self.avl.search(num, steps_ret=True)
        return val, steps

    def pending_sorted(self):
        """Orders not yet dispatched, sorted via merge_sort_orders."""
        pend = [o for o in self.orders if o["status"] == "PENDING"]
        return merge_sort_orders(pend)

    def _seed_labs(self):
        self.trie = Trie()
        for loc in self.locations:
            self.trie.insert(loc["name"])

        self.cost_model = Polynomial([(0.8, 2), (1.2, 1), (35, 0)])

        self.symbol = HashTableChaining(size=7, hashfn=hash_division)
        for loc in self.locations:
            self.symbol.insert(loc["id"], loc["name"])

    def dispatch_pq_snapshot(self):
        """Array-MIN-HEAP dispatch queue rebuilt from pending orders;
        key = (priority, arrival_seq) so Express pops first, FIFO within."""
        pq = MinHeapPQ()
        for order in self.pending_sorted():
            pq.push((order["priority"], order["seq"]), order["number"])
        return pq

STORE = Store()

def json_error(msg, code=400):
    return jsonify({"error": msg}), code

def get_location_or_none(lid):
    if not isinstance(lid, int) or lid < 0:
        return None
    if lid >= len(STORE.locations):
        return None
    return STORE.locations[lid]

def validate_order_payload(data):
    """POST /api/orders input validation -> (clean, error_response)."""
    if not isinstance(data, dict):
        return None, json_error("body must be a JSON object")
    customer = data.get("customer")
    location = data.get("location")
    priority = data.get("priority")
    weight = data.get("weight")
    if not isinstance(customer, str) or not customer.strip():
        return None, json_error("'customer' must be a non-empty string")
    if not isinstance(location, int):
        return None, json_error("'location' must be an integer location id")
    if get_location_or_none(location) is None:
        return None, json_error("unknown location id %r" % (location,))
    if priority not in (1, 2, 3):
        return None, json_error("'priority' must be 1 (Express), 2 (Standard) or 3 (Economy)")
    if not isinstance(weight, (int, float)) or weight <= 0 or weight > 500:
        return None, json_error("'weight' must be a number in (0, 500] kg")
    return {"customer": customer.strip(), "location": location,
            "priority": priority, "weight": float(weight)}, None

def order_public(order):
    """JSON view of one order (dict use = fine, output shaping only)."""
    loc = STORE.locations[order["location"]]
    return {
        "id": order["id"], "customer": order["customer"],
        "location": order["location"], "location_name": loc["name"],
        "priority": order["priority"], "weight": order["weight"],
        "status": order["status"], "driver": order["driver"],
        "seq": order["seq"],
    }

def validate_stops(raw_stops):
    """Turn ["1", 9, ...] ids into ints; error string -> (list, None)."""
    if not isinstance(raw_stops, list):
        return None, "stops must be a JSON array of location ids"
    stops = []
    for s in raw_stops:
        if not isinstance(s, int) or s < 0:
            return None, "each stop must be a non-negative integer location id"
        if s >= len(STORE.locations):
            return None, "location %d does not exist" % s
        if s == SEED_DEPOT_ID:
            return None, "the depot cannot be its own stop"
        if s in stops:
            return None, "stop %d is duplicated" % s
        stops.append(s)
    return stops, None

def validate_depot(raw_depot):
    """Depot defaults to id 0; must be an existing location."""
    if raw_depot is None:
        return 0, None
    if not isinstance(raw_depot, int) or raw_depot < 0 or \
            raw_depot >= len(STORE.locations):
        return None, "depot must be a valid location id"
    return raw_depot, None

SEED_DEPOT_ID = 0

def route_geometry(depot, stops):
    """Expand the stop sequence into full ROAD paths per hop (node id lists)
    using the Dijkstra prevmap, so the map animation follows real streets."""
    hops = []
    prev_stop = depot
    for stop in stops:
        seg = []
        u = stop
        while u != prev_stop:
            seg.append(u)
            u = STORE.prevmap[prev_stop][u]
        seg.reverse()
        hops.append([prev_stop] + seg)
        prev_stop = stop
    back = []
    u = depot
    while u != stops[-1]:
        back.append(u)
        u = STORE.prevmap[stops[-1]][u]
    back.reverse()
    hops.append(back)
    return hops

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/state")
def api_state():
    s = STORE
    return jsonify({
        "locations": s.locations,
        "roads": s.roads,
        "orders": [order_public(o) for o in s.orders],
        "drivers": s.drivers.snapshot(),
        "pending_sorted": [o["id"] for o in s.pending_sorted()],
        "deliveries": s.deliveries[-8:],
        "count": {"locations": len(s.locations), "roads": len(s.roads),
                  "orders": len(s.orders)},
    })

@app.route("/api/locations", methods=["POST"])
def api_locations_add():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return json_error("body must be a JSON object")
    name = data.get("name")
    lat, lng = data.get("lat"), data.get("lng")
    x, y = data.get("x"), data.get("y")
    if not isinstance(name, str) or not name.strip():
        return json_error("'name' must be a non-empty string")
    has_geo = lat is not None or lng is not None
    has_grid = x is not None or y is not None
    if has_grid and (not isinstance(x, int) or not isinstance(y, int) or
                     not (0 <= x <= 100) or not (0 <= y <= 100)):
        return json_error("'x' and 'y' must be integers within the 0-100 grid")
    if not has_geo and not has_grid:
        return json_error("provide 'lat' and 'lng', or legacy 'x' and 'y'")
    if has_grid and not has_geo:
        lat, lng = STORE._xy_latlng(x, y)
    lid, err = STORE.add_location(lat, lng, name.strip())
    if err:
        return json_error(err)
    loc = STORE.locations[lid]
    STORE.undo.push(["ADD_LOC", loc["x"], loc["y"]])
    return jsonify({"ok": True, "id": lid, "name": loc["name"],
                    "lat": loc["lat"], "lng": loc["lng"],
                    "x": loc["x"], "y": loc["y"]}), 201

ENGINE_LABELS = {
    "exact": "EXACT (BACKTRACKING)",
    "nn": "NEAREST NEIGHBOUR",
    "nn2opt": "NEAREST NEIGHBOUR + 2-OPT",
    "auto": "AUTO",
}

def stop_priority_map(stops):
    """Location -> best pending order priority at it (Express=1 wins)."""
    prios = {}
    for order in STORE.orders:
        if order["status"] == "PENDING" and order["location"] in stops:
            cur = prios.get(order["location"])
            if cur is None or order["priority"] < cur:
                prios[order["location"]] = order["priority"]
    return prios

def solve_route_physarum(stops, depot, priority_first=False):
    """PHYSARUM LEGS engine: every depot/stop leg is found by the slime-mold
    tube adaptation (cached in the project's hash table), while the stop
    ORDER still comes from the classic exact / NN+2-OPT engine. Dijkstra km
    ride along as ground truth; a leg that misses the 1% bar falls back."""
    if len(stops) > 8:
        return None, "PHYSARUM LEGS engine is capped at 8 stops (36 pair solves)"
    base, err = solve_route(stops, depot, "auto", priority_first)
    if err:
        return None, err
    order = base["stops"]
    walk = [depot] + order + [depot]
    prios = stop_priority_map(stops)
    legs, cum, hops = [], 0.0, []
    worst_diff, phys_ms, bad = 0.0, 0.0, 0
    for i in range(len(walk) - 1):
        a, b = walk[i], walk[i + 1]
        phops, km, ok, diff, pms = physarum_pair_leg(a, b)
        phys_ms += pms
        worst_diff = max(worst_diff, diff)
        bad += 0 if ok else 1
        if not phops:
            return None, "locations %s and %s are not connected" % (a, b)
        for h in phops:
            if not hops or hops[-1] != h:
                hops.append(h)
        leg_km = round(km, 1)
        cum = round(cum + leg_km, 1)
        legs.append({
            "i": i, "from": a, "to": b,
            "from_name": STORE.locations[a]["name"],
            "to_name": STORE.locations[b]["name"],
            "km": leg_km, "cum": cum,
            "prio": None if b == depot else prios.get(b),
        })
    base["legs"] = legs
    base["geometry"] = hops
    base["distance"] = cum
    base["cum_total"] = cum
    base["cost"] = round(STORE.cost_model.evaluate(cum), 2)
    base["eta_min"] = int(round(cum / 30.0 * 60))
    base["engine_label"] = "PHYSARUM LEGS + " + base["engine_label"]
    base["algorithm"] = "PHYSARUM ADAPTATION (TERO 2010) LEGS + " + base["algorithm"]
    base["dsa_used"] = base["dsa_used"] + ["PHYSARUM CG", "HASH TABLE"]
    base["physarum"] = {
        "pair_ms": round(phys_ms, 1),
        "pairs": len(walk) - 1,
        "worst_diff_pct": round(worst_diff, 3),
        "fallback_pairs": bad,
        "note": "LEG DISTANCES FROM SLIME TUBE ADAPTATION; DIJKSTRA IS THE "
                "REFERENCE (%d/%d LEGS MISSING THE 1%% BAR USED DIJKSTRA KM)"
                % (bad, len(walk) - 1),
    }
    if bad:
        base["fallback_note"] = ("PHYSARUM LEGS: %d OF %d LEGS FELL BACK TO "
                                 "DIJKSTRA KM (TUBES MISSED THE 1%% BAR)"
                                 % (bad, len(walk) - 1))
    return base, None

def solve_route(stops, depot, engine, priority_first=False):
    """Shared solve for /api/optimize and /api/optimize/compare.
    Returns dict with order / geometry / legs / engine label / notes or an
    error message string (caller turns it into a 4xx body)."""
    notes = []
    fallback_note = None

    def run(group, start, eng, note=None):
        """Run one engine pass; fall back to auto when exact gets too big."""
        mode = eng
        if mode == "exact" and len(group) > 9:
            mode = "auto"
            if note is not None:
                notes.append(note)
        return STORE.optimizer.optimize(group, start, mode=mode)

    if priority_first:
        prios = stop_priority_map(stops)
        express = [s for s in stops if prios.get(s) == 1]
        rest = [s for s in stops if prios.get(s) != 1]
        if not express or not rest:
            priority_first = False
    order, ms, steps, pruned = [], 0.0, 0, 0
    start = depot
    if priority_first:
        r1 = run(express, depot, engine, "EXACT engine capped at 9; AUTO used for the express group")
        order += r1["order"]
        ms += r1["ms"]
        steps += r1["steps"]
        pruned += r1["pruned"]
        start = order[-1] if order else depot
        r2 = run(rest, start, engine, "EXACT engine capped at 9; AUTO used for the rest group")
        order += r2["order"]
        ms += r2["ms"]
        steps += r2["steps"]
        pruned += r2["pruned"]
        priority_note = "EXPRESS (E=P1) STOPS ARE VISITED FIRST, THEN THE REST - " \
                        "THE OVERALL ROUTE IS THEN APPROXIMATE, NOT OPTIMAL"
        engine_used = r1["engine"] if r1["engine"] == r2["engine"] else "auto"
        algo_used = r1["algorithm"] if r1["engine"] == r2["engine"] else \
            "GROUPED SEQ (" + r1["engine"] + " + " + r2["engine"] + ")"
        complexity_used = r1["complexity"]
    else:
        r0 = run(stops, depot, engine, "EXACT engine is capped at 9 stops - ran AUTO (NN + 2-OPT) instead")
        if notes:
            fallback_note = notes[0]
        order = r0["order"]
        ms += r0["ms"]
        steps += r0["steps"]
        pruned += r0["pruned"]
        engine_used = r0["engine"]
        algo_used = r0["algorithm"]
        complexity_used = r0["complexity"]
        priority_note = None

    if order and (not priority_first) and STORE.optimizer.tour_cost(order, depot) < 1e-12:
        return None, "route could not be solved for these stops"
    hops = route_geometry(depot, order)
    total = STORE.optimizer.tour_cost(order, depot)
    costs = STORE.cost_model.evaluate(total)

    prios = stop_priority_map(stops)
    legs, cum = [], 0.0
    Walk = [depot] + order + [depot]
    for i in range(len(Walk) - 1):
        a, b = Walk[i], Walk[i + 1]
        km = round(STORE.dist[a][b], 1)
        cum = round(cum + km, 1)
        legs.append({
            "i": i, "from": a, "to": b,
            "from_name": STORE.locations[a]["name"],
            "to_name": STORE.locations[b]["name"],
            "km": km, "cum": cum,
            "prio": None if b == depot else prios.get(b),
        })
    return {
        "depot": depot,
        "stops": order,
        "stop_names": [STORE.locations[i]["name"] for i in order],
        "geometry": hops,
        "distance": total,
        "cum_total": cum,
        "cost": round(costs, 2),
        "cost_terms": STORE.cost_model.to_display().replace("x", "d"),
        "eta_min": int(round(total / 30.0 * 60)),
        "algorithm": algo_used,
        "engine_label": ENGINE_LABELS[engine_used] if engine_used in ENGINE_LABELS else engine_used,
        "complexity": complexity_used,
        "ms": round(ms, 3),
        "nodes_explored": steps,
        "pruned": pruned,
        "legs": legs,
        "dsa_used": ["STACK", "MIN-HEAP", "DIJKSTRA", "GRAPH", "SPARSE MATRIX"],
        "priority_note": priority_note,
        "fallback_note": fallback_note,
        "exact_cap": stops and len(stops) > 9,
    }, None

@app.route("/api/optimize", methods=["POST"])
def api_optimize():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return json_error("body must be a JSON object")
    stops, err = validate_stops(data.get("stops"))
    if err:
        return json_error(err)
    depot, err = validate_depot(data.get("depot"))
    if err:
        return json_error(err)
    engine = data.get("engine") or data.get("mode") or "auto"
    if engine not in ("exact", "nn", "nn2opt", "heuristic", "auto", "physarum"):
        return json_error("engine must be auto | exact | nn | nn2opt | physarum")
    if not stops:
        return json_error("select at least one stop to optimize")
    if engine == "physarum" and len(stops) > 8:
        return json_error("PHYSARUM LEGS engine is capped at 8 stops "
                          "(36 pair solves)")
    priority_first = bool(data.get("priority_first"))
    if engine == "physarum":
        result, err = solve_route_physarum(stops, depot, priority_first)
        if err:
            return json_error(err)
        return jsonify(result)
    if engine != "auto" and len(stops) > 12:
        return json_error("at most 12 stops per route run")
    priority_first = bool(data.get("priority_first"))
    result, err = solve_route(stops, depot, engine, priority_first)
    if err:
        return json_error(err)
    return jsonify(result)

@app.route("/api/optimize/compare", methods=["POST"])
def api_optimize_compare():
    """Run every engine on the same stop set; best row = lowest km."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return json_error("body must be a JSON object")
    stops, err = validate_stops(data.get("stops"))
    if err:
        return json_error(err)
    depot, err = validate_depot(data.get("depot"))
    if err:
        return json_error(err)
    if not stops:
        return json_error("select at least one stop to compare")
    rows = []
    for engine in ("exact", "nn", "nn2opt", "auto"):
        label = ENGINE_LABELS[engine]
        if engine == "exact" and len(stops) > 9:
            rows.append({"engine": label, "km": None, "ms": 0,
                         "note": "SKIPPED (EXACT CAPS AT 9 STOPS)"})
            continue
        r = STORE.optimizer.optimize(stops, depot, mode=engine)
        rows.append({"engine": label, "km": r["cost"], "ms": round(r["ms"], 3),
                     "algorithm": r["algorithm"], "note": None})
    best = None
    for row in rows:
        if row["km"] is not None and (best is None or row["km"] < best["km"]):
            best = row
    for row in rows:
        row["best"] = False
    if best is not None:
        best["best"] = True
    return jsonify({"rows": rows, "stops": len(stops)})

@app.route("/api/drivers/assign", methods=["POST"])
def api_drivers_assign():
    """Rotate the round-robin circular queue: the front driver is assigned
    (popped) and re-enqueued behind everyone else."""
    if STORE.drivers.is_empty():
        return json_error("no drivers registered", 422)
    driver = STORE.drivers.dequeue()
    STORE.drivers.enqueue(driver)
    return jsonify({"assigned": driver, "queue": STORE.drivers.snapshot()})

def _lcg_next(state):
    """Hand-written 32-bit LCG: x = (1103515245*x + 12345) mod 2^31.
    state is a one-element list so the caller keeps sequencing."""
    val = (1103515245 * state[0] + 12345) % 2147483648
    state[0] = val
    return val

def physarum_dijkstra_ref(a, b):
    """Exact Dijkstra twin for one pair; returns (path_km, hops, ms)."""
    t0 = time.perf_counter()
    hops, km, _dist = shortest_path(STORE.g, a, b)
    ms = (time.perf_counter() - t0) * 1000.0
    return None if hops is None else (km, hops, ms)

def physarum_pair_leg(a, b):
    """Physarum solve for one pair with the project's hash-table cache.

    Cache value = [hops, km, ok, diff_pct, phys_ms] where ok means the tube
    path matched Dijkstra's km within 1%. Falls back to Dijkstra hops when
    the walk fails or misses the 1% bar (Dijkstra is the answer of record)."""
    if a > b:
        a, b = b, a
    key = a * 100 + b
    hit, _probe_steps = STORE.leg_cache.lookup(key)
    if hit is not None:
        return hit
    res = STORE.pnet.solve(a, b)
    ref = physarum_dijkstra_ref(a, b)
    diff = 0.0
    if ref is None:
        val = [[], float("inf"), False, 0.0, res["ms"]]
    elif res["path"] is not None:
        dk = ref[0]
        diff = abs(res["km"] - dk) / dk * 100 if dk > 0 else 0.0
        if diff <= 1.0:
            val = [res["path"], round(dk, 2), True, diff, res["ms"]]
        else:
            val = [ref[1], round(dk, 2), False, diff, res["ms"]]
    else:
        val = [ref[1], round(ref[0], 2), False, 0.0, res["ms"]]
    STORE.leg_cache.insert(key, val)
    return val

@app.route("/api/physarum", methods=["POST"])
def api_physarum():
    """Single source->sink slime solve. Dijkstra rides along as ground
    truth; the answer of record switches to Dijkstra if the tubes miss."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return json_error("body must be a JSON object")
    src, err = validate_depot(data.get("source"))
    if err:
        return json_error(err)
    dst, err = validate_depot(data.get("sink"))
    if err:
        return json_error(err)
    if src == dst:
        return json_error("source and sink must be two different locations")

    def num(name, lo, hi, default):
        v = data.get(name, default)
        if v is None:
            return float(default), None
        if not isinstance(v, (int, float)) or isinstance(v, bool) \
                or not (lo <= v <= hi):
            return None, "%s must be a number in [%s, %s]" % (name, lo, hi)
        return float(v), None

    g, err = num("g", 0.25, 4.0, 1.5)
    if err: return json_error(err)
    mu, err = num("mu", 0.0, 3.0, 1.0)
    if err: return json_error(err)
    dt, err = num("dt", 0.01, 0.5, 0.1)
    if err: return json_error(err)
    I0, err = num("I0", 0.1, 10.0, 1.0)
    if err: return json_error(err)

    res = STORE.pnet.solve(src, dst, g=g, mu=mu, dt=dt, I0=I0)
    ref = physarum_dijkstra_ref(src, dst)
    if ref is None:
        return json_error("source and sink are not connected", 422)
    djk_km, djk_hops, djk_ms = ref
    phys_km = res["km"]
    path, km, note = res["path"], phys_km, None
    within = res["path"] is not None and abs(phys_km - djk_km) / djk_km * 100 <= 1.0
    if res["path"] is None:
        path, km = djk_hops, round(djk_km, 2)
        note = "TUBE WALK FAILED - USING DIJKSTRA PATH"
    elif not within:
        path, km = djk_hops, round(djk_km, 2)
        note = "DID NOT CONVERGE TO OPTIMUM - USING DIJKSTRA PATH"
    elif abs(phys_km - djk_km) / djk_km * 100 > 0.0:
        km = round(djk_km, 2)
        note = "TWO NEAR-EQUAL PATHS - SHORTER (DIJKSTRA) REPORTED"
    return jsonify({
        "ok": True, "source": src, "sink": dst,
        "path": path, "km": round(km, 2),
        "physarum_km": round(phys_km, 2),
        "dijkstra_km": round(djk_km, 2),
        "dijkstra_path": djk_hops,
        "iterations": res["iterations"], "converged": res["converged"],
        "converged_at": res.get("converged_at"),
        "conv_tol": res.get("conv_tol"),
        "within_1pct": within, "note": note,
        "frames": res["frames"],
        "edges": STORE.g.edges,
        "physarum_ms": res["ms"], "dijkstra_ms": round(djk_ms, 3),
        "tie_note": res["tie_note"],
    })

@app.route("/api/physarum/growth", methods=["POST"])
def api_physarum_growth():
    """ADVANCED (Tokyo-rail): demand pairs over the SELECTED stops drive a
    few physarum iterations each; D accumulates, weak tubes are pruned and
    the surviving network is compared to the Kruskal MST total."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return json_error("body must be a JSON object")
    stops, err = validate_stops(data.get("stops"))
    if err:
        return json_error(err)
    if len(stops) < 2:
        return json_error("growth mode needs at least 2 stops")

    def num(name, lo, hi, default):
        v = data.get(name, default)
        if not isinstance(v, (int, float)) or isinstance(v, bool)\
                or not (lo <= v <= hi):
            return None, "%s must be a number in [%s, %s]" % (name, lo, hi)
        return float(v), None

    pairs_n = data.get("pairs", 8)
    if not isinstance(pairs_n, int) or isinstance(pairs_n, bool)\
            or not (1 <= pairs_n <= 24):
        return json_error("pairs must be an integer in [1, 24]")
    iters = data.get("iters", 6)
    if not isinstance(iters, int) or isinstance(iters, bool)\
            or not (1 <= iters <= 30):
        return json_error("iters must be an integer in [1, 30]")
    seed = data.get("seed", 7)
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        return json_error("seed must be a non-negative integer")
    prune, err = num("prune", 0.05, 0.6, 0.15)
    if err: return json_error(err)
    g, err = num("g", 0.25, 4.0, 1.5)
    if err: return json_error(err)
    mu, err = num("mu", 0.0, 3.0, 1.0)
    if err: return json_error(err)
    dt, err = num("dt", 0.01, 0.5, 0.1)
    if err: return json_error(err)
    I0, err = num("I0", 0.1, 10.0, 1.0)
    if err: return json_error(err)

    net = PhysarumNetwork(STORE.g.n, STORE.g.edges)
    state = [seed % 2147483648]
    n = len(STORE.locations)
    frames, pairs_used = [], []
    for t in range(pairs_n):
        a = _lcg_next(state) % n
        b = _lcg_next(state) % n
        while b == a:
            b = _lcg_next(state) % n
        pairs_used.append([a, b])
        net.run_pair(a, b, g=g, mu=mu, dt=dt, I0=I0, iters=iters)
        frames.append({"pair": [a, b], "D": list(net.D)})

    dmax = max(net.D)
    thresh = prune * dmax
    surviving, removed = [], 0
    for e in range(len(net.D)):
        if net.D[e] >= thresh:
            surviving.append([net.edges[e][0], net.edges[e][1], net.L[e]])
        else:
            removed += 1
    total_length = round(sum(seg[2] for seg in surviving), 1)

    sub = Graph(len(STORE.locations))
    for u, v, w in surviving:
        sub.add_edge(u, v, w)
    sub_dist, _prev = dijkstra_all_pairs(sub)
    INF = float("inf")
    sd, cnt = 0.0, 0
    for i in range(len(stops)):
        for j in range(i + 1, len(stops)):
            d = sub_dist[stops[i]][stops[j]]
            if d != INF:
                sd += d
                cnt += 1
    avg_stop_path = round(sd / cnt, 2) if cnt else None

    mst_edges, mst_total = kruskal_mst(STORE.g)
    full_total = round(sum(r["w"] for r in STORE.roads), 1)
    return jsonify({
        "ok": True, "seed": seed, "pairs_used": pairs_used,
        "frames": frames, "edges": STORE.g.edges,
        "surviving": surviving, "removed": removed,
        "prune": round(prune, 3),
        "total_length": total_length,
        "avg_stop_path": avg_stop_path,
        "mst_edges": mst_edges,
        "mst_total": None if mst_total is None else round(mst_total, 1),
        "full_total": full_total,
        "verdict": ("SLIME %.1f KM VS MST %.1f KM (FULL GRAPH %.1f KM)"
                    % (total_length, mst_total, full_total)
                    if mst_total is not None else "SLIME %.1f KM (GRAPH DISCONNECTED)"
                    % total_length),
    })

@app.route("/api/cost-model", methods=["POST"])
def api_cost_model():
    """Polynomial transport-cost panel: A d^2 + B d + C evaluated on d."""
    data = request.get_json(silent=True) or {}
    try:
        a = float(data.get("a", 0.8))
        b = float(data.get("b", 1.2))
        c = float(data.get("c", 35))
        d = float(data.get("d", 0))
    except (TypeError, ValueError):
        return json_error("a, b, c, d must be numbers")
    poly = Polynomial([(a, 2), (b, 1), (c, 0)])
    return jsonify({"terms": poly.terms(), "display": poly.to_display(),
                    "distance": d, "cost": round(poly.evaluate(d), 2)})

@app.route("/api/orders", methods=["POST"])
def api_orders_add():
    clean, err = validate_order_payload(request.get_json(silent=True))
    if err:
        return err
    order = STORE.create_order(**clean)
    return jsonify({"ok": True, "order": order_public(order)}), 201

@app.route("/api/orders/undo", methods=["POST"])
def api_orders_undo():
    if STORE.undo.is_empty():
        return json_error("nothing to undo", 422)
    action = STORE.undo.pop()
    if action[0] == "ADD":
        STORE.remove_order(action[1])
        return jsonify({"ok": True, "undone": "added %s" % action[1]})
    if action[0] == "DISPATCH":
        for o in STORE.orders:
            if o["id"] == action[1]:
                o["status"] = "PENDING"
                o["driver"] = None
                if o["number"] in STORE.deliveries:
                    STORE.deliveries.remove(o["number"])
                return jsonify({"ok": True, "undone": "dispatch %s" % action[1]})
        return json_error("order missing from store", 500)
    if action[0] == "ADD_LOC":

        lid = len(STORE.locations) - 1
        STORE.locations = STORE.locations[:lid]
        STORE.roads = [r for r in STORE.roads
                       if r["u"] != lid and r["v"] != lid]
        STORE.g.adjacency = STORE.g.adjacency[:lid]
        STORE.g.n = lid
        STORE.g.edges = [e for e in STORE.g.edges if e[0] < lid and e[1] < lid]
        STORE._rebuild_matrices()
        return jsonify({"ok": True, "undone": "location #%d" % lid})
    return json_error("unknown undo entry", 500)

@app.route("/api/orders/dispatch", methods=["POST"])
def api_orders_dispatch():
    pq = STORE.dispatch_pq_snapshot()
    if pq.is_empty():
        return json_error("no pending orders to dispatch", 422)
    key, number = pq.pop_min()
    for o in STORE.orders:
        if o["number"] == number:
            o["status"] = "DISPATCHED"
            driver = STORE.drivers.dequeue()
            STORE.drivers.enqueue(driver)
            o["driver"] = driver
            STORE.deliveries.append(number)
            STORE.undo.push(["DISPATCH", o["id"]])
            return jsonify({"ok": True, "order": order_public(o), "queue_key": key})
    return json_error("dispatch queue stale", 500)

@app.route("/api/orders/sorted")
def api_orders_sorted():
    """Sorted list view = the project's own merge sort (stable)."""
    out = []
    for o in merge_sort_orders(STORE.orders):
        out.append(order_public(o))
    return jsonify({"algo": "merge_sort (stable): priority ASC, weight DESC",
                    "orders": out})

@app.route("/api/orders/<order_id>")
def api_orders_get(order_id):
    hit = STORE.lookup_order(order_id)
    if hit is None:
        return json_error("order id must look like ORD-1234", 400)
    order, steps = hit
    if order is None:
        return json_error("no order with id %s" % order_id, 404)

    num = order["number"]
    window = STORE.bplus.range_scan(num - 2, num + 2)
    return jsonify({"order": order_public(order),
                    "index": "AVL tree over order number",
                    "search_steps": steps,
                    "bplus_chain": ["ORD-%d" % k for k, _v in window
                                    if _v is not None]})

@app.route("/api/network")
def api_network():
    s = STORE
    prims_edges, prims_total = prim_mst(s.g)
    krusk_edges, krusk_total = kruskal_mst(s.g)
    bfs, levels = bfs_order(s.g, 0)
    return jsonify({
        "components": s.components,
        "component_count": len(s.components),
        "prim": {"edges": prims_edges, "total": prims_total},
        "kruskal": {"edges": krusk_edges, "total": krusk_total},
        "bfs_from_depot": {"order": bfs, "levels": levels},
        "density": round(s.sparse.density(), 3),
        "sparse_rows": s.sparse.as_rows_json(),
        "sparse_shape": [s.g.n, s.g.n],
        "adjacency_count": s.g.edge_count(),
    })

@app.route("/api/traverse")
def api_traverse():
    mode = (request.args.get("mode") or "bfs").lower()
    if mode not in ("bfs", "dfs"):
        return json_error("mode must be bfs or dfs")
    start_raw = request.args.get("start")
    if start_raw is None:
        return json_error("query param start is required")
    try:
        start = int(start_raw)
    except ValueError:
        return json_error("start must be an integer location id")
    if start < 0 or start >= len(STORE.locations):
        return json_error("start location %d does not exist" % start)
    if mode == "bfs":
        order, levels = bfs_order(STORE.g, start)
        structure = "ArrayDeque fringe (FIFO)"
    else:
        order = dfs_order(STORE.g, start)
        levels = None
        structure = "DynStack fringe (LIFO, recursion simulated)"
    return jsonify({"mode": mode, "start": start, "order": order,
                    "levels": levels, "structure": structure})

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "")
    if not q.strip():
        return jsonify({"q": q, "matches": []})
    matches = STORE.trie.autocomplete(q.strip(), limit=8)
    out = []
    for name in matches:
        for loc in STORE.locations:
            if loc["name"] == name:
                out.append(loc)
                break
    return jsonify({"q": q, "matches": out})

@app.route("/api/sort-bench", methods=["POST"])
def api_sort_bench():
    data = request.get_json(silent=True) or {}
    try:
        size = int(data.get("size", 400))
        range_max = int(data.get("range", 60))
    except (TypeError, ValueError):
        return json_error("size and range must be integers")
    if size < 2 or size > 5000:
        return json_error("size must be between 2 and 5000")
    if range_max < 5 or range_max > 20000:
        return json_error("range must be between 5 and 20000 (counting keys)")
    arr = [random.randint(0, range_max - 1) for _ in range(size)]
    bench = benchmark_all(arr)
    ext = external_sort(arr[:80], chunk_size=10)
    return jsonify({
        "results": bench,
        "input": {"size": size, "range": range_max},
        "external": {"chunks": ext["chunks"], "passes": ext["passes"],
                     "final": ext["final"], "comparisons": ext.get("comparisons_total")},
    })

@app.route("/api/hash-demo", methods=["GET", "POST"])
def api_hash_demo():
    data = request.get_json(silent=True) or {}
    if request.args.get("key") and not data:
        data["key"] = request.args.get("key")
    raw = data.get("key")
    if isinstance(raw, str):
        raw = raw.strip().upper()
        if raw.startswith("ORD-"):
            try:
                key = int(raw[4:])
            except ValueError:
                return json_error("order id suffix must be numeric")
        elif raw.isdigit():
            key = int(raw)
        else:
            return json_error("key must be an order number or ORD-<number>")
    elif isinstance(raw, int):
        key = raw
    else:
        return json_error("key must be integers-built (order number)")
    fn = {1: hash_division, 2: hash_mid_square, 3: hash_folding,
          "division": hash_division, "mid-square": hash_mid_square,
          "folding": hash_folding}.get(data.get("function", 1))
    if fn is None:
        return json_error("function must be division | mid-square | folding")
    chain = HashTableChaining(size=11, hashfn=fn)
    open_lin = HashTableOpen(size=11, resolution="linear", hashfn=fn)
    open_dbl = HashTableOpen(size=11, resolution="double", hashfn=fn)
    for num in range(1000, 1000 + max(8, (key - 999))):
        for table in (chain, open_lin, open_dbl):
            table.insert(num, "ORD-%d" % num)
    lookup = chain.lookup(key)[1]
    open_lookup = open_lin.lookup(key)[1]
    return jsonify({
        "key": key,
        "bucket": fn(key, 11),
        "chains": chain.snapshot(),
        "chain_collisions": chain.collisions,
        "open_linear": open_lin.snapshot(),
        "open_double": open_dbl.snapshot(),
        "lookup_steps": {"chained": lookup, "open_linear": open_lookup},
    })

@app.route("/api/search-demo", methods=["POST"])
def api_search_demo():
    """Linear vs binary search step counts on a sorted id array."""
    data = request.get_json(silent=True) or {}
    try:
        n = int(data.get("n", 50))
        target = data.get("target")
    except (TypeError, ValueError):
        return json_error("n and target must be integers")
    if n < 1 or n > 2000:
        return json_error("n must be in [1, 2000]")
    ids = [1000 + 7 * i for i in range(n)]
    if target is None:
        target = ids[random.randint(0, n - 1)]
    else:
        try:
            target = int(target)
        except (TypeError, ValueError):
            return json_error("target must be an integer")
    li, lsteps = linear_search(ids, target)
    bi, bsteps = binary_search(ids, target)
    return jsonify({"array": ids[:12] + ["..."], "n": n, "target": target,
                    "linear": {"index": li, "steps": lsteps},
                    "binary": {"index": bi, "steps": bsteps}})
