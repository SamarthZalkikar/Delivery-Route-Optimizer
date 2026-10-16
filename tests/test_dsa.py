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
from dsa.optimizer import RouteOptimizer

class TestDynStack(unittest.TestCase):
    def test_lifo_and_resize(self):
        s = DynStack()
        for i in range(100):
            s.push(i)
        for i in range(99, -1, -1):
            self.assertEqual(s.pop(), i)
        self.assertTrue(s.is_empty())
        self.assertLessEqual(len(s._a), 8)

    def test_peek_and_errors(self):
        s = DynStack()
        with self.assertRaises(IndexError):
            s.pop()
        s.push(7)
        self.assertEqual(s.peek(), 7)
        self.assertEqual(len(s), 1)

class TestTwoStacks(unittest.TestCase):
    def test_both_stacks_independent(self):
        ts = TwoStacks(6)
        ts.push0(1); ts.push0(2)
        ts.push1("a"); ts.push1("b"); ts.push1("c")
        self.assertEqual(ts.sizes(), (2, 3))
        self.assertEqual(ts.pop1(), "c")
        self.assertEqual(ts.pop0(), 2)
        with self.assertRaises(OverflowError):
            for i in range(10):
                ts.push0(i)

class TestNStacksOneArray(unittest.TestCase):
    def test_interleaved(self):
        ns = NStacksOneArray(3, 9)
        ns.push(0, 1); ns.push(1, 2); ns.push(2, 3)
        ns.push(0, 10); ns.push(0, 100)
        self.assertEqual(ns.pop(0), 100)
        self.assertEqual(ns.pop(0), 10)
        self.assertEqual(ns.pop(1), 2)
        self.assertEqual(ns.pop(2), 3)
        self.assertEqual(ns.pop(0), 1)
        with self.assertRaises(IndexError):
            ns.pop(0)
        for i in range(9):
            ns.push(0, i)
        with self.assertRaises(OverflowError):
            ns.push(1, 99)

class TestPriorityQueues(unittest.TestCase):
    def test_minheap_lifecycle(self):
        pq = MinHeapPQ()
        for k in [5, 1, 9, 2, 2, 7]:
            pq.push(k, None)
        got = [pq.pop_min() for _ in range(6)]
        self.assertEqual(got, [1, 2, 2, 5, 7, 9])
        self.assertTrue(pq.is_empty())
        with self.assertRaises(IndexError):
            pq.pop_min()

    def test_minheap_key_value(self):
        pq = MinHeapPQ()
        pq.push(3, "c"); pq.push(1, "a"); pq.push(2, "b")
        self.assertEqual(pq.pop_min()[1], "a")
        self.assertEqual(pq.peek()[1], "b")

    def test_sorted_list_pq(self):
        pq = SortedListPQ()
        for k in [4, 1, 3, 1, 5]:
            pq.push(k, None)
        got = [pq.pop_min() for _ in range(5)]
        self.assertEqual(got, [1, 1, 3, 4, 5])

class TestCircularQueue(unittest.TestCase):
    def test_wraparound(self):
        q = CircularQueue(5)
        self.assertEqual(q.cap, 5)
        for x in [1, 2]:
            q.enqueue(x)
        self.assertEqual(q.dequeue(), 1)
        q.enqueue(3); q.enqueue(4); q.enqueue(5)
        self.assertEqual(q.snapshot(), [2, 3, 4, 5])
        self.assertTrue(q.is_full())
        with self.assertRaises(OverflowError):
            q.enqueue(6)
        self.assertEqual(q.dequeue(), 2)

class TestDeque(unittest.TestCase):