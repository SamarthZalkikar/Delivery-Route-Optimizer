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