"""Tests for every data structure in the dsa/ package."""
import unittest
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsa.linear import (DynStack, TwoStacks, NStacksOneArray, MinHeapPQ,
                        SortedListPQ, CircularQueue, ArrayDeque)
from dsa.linked import (SinglyLinkedList, DoublyLinkedList, HeaderLinkedList,
                        CircularLinkedList, Polynomial)
from dsa.dsu import DSU
from dsa.trie import Trie
from dsa.hashing import (hash_division, hash_mid_square, hash_folding,
                         HashTableChaining, HashTableOpen)
from dsa.sorting import (shell_sort, quick_sort, merge_sort, heap_sort,
                         counting_sort, external_sort, linear_search,
                         binary_search, merge_sort_orders, benchmark_all)
from dsa.trees import BST, ThreadedBST, AVLTree, BTree, BPlusTree
from dsa.graph import (Graph, bfs_order, dfs_order, connected_components,
                       dijkstra, shortest_path, prim_mst, kruskal_mst,
                       dijkstra_all_pairs)
from dsa.sparse import SparseMatrix