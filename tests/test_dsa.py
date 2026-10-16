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
    def test_both_ends(self):
        d = ArrayDeque()
        d.push_back(2); d.push_front(1); d.push_back(3)
        self.assertEqual(d.pop_front(), 1)
        self.assertEqual(d.pop_back(), 3)
        self.assertEqual(len(d), 1)

    def test_restricted_variants(self):
        from dsa.linear import DequeIR, DequeOR
        ir = DequeIR()
        ir.push_back(1)
        with self.assertRaises(Exception):
            ir._forbidden("push_front")
        self.assertEqual(ir._q.pop_front(), 1)
        irq = DequeOR()
        irq.push_front(9); irq.push_back(8)
        self.assertEqual(irq.pop_front(), 9)

class TestLinkedLists(unittest.TestCase):
    def test_sll(self):
        l = SinglyLinkedList()
        l.push_back(1); l.push_back(2); l.push_front(0)
        self.assertEqual(l.to_list(), [0, 1, 2])
        self.assertEqual(l.search(2), 2)
        self.assertTrue(l.delete_val(1))
        self.assertEqual(l.to_list(), [0, 2])
        self.assertFalse(l.delete_val(9))
        self.assertEqual(len(l), 2)

    def test_dll_reverse(self):
        d = DoublyLinkedList([1, 2, 3])
        self.assertEqual(d.to_list_reverse(), [3, 2, 1])
        d.delete_node(d.head)
        self.assertEqual(d.to_list(), [2, 3])

    def test_header_list_count(self):
        h = HeaderLinkedList()
        h.push_back("x"); h.push_back("y")
        self.assertEqual(len(h), 2)
        self.assertEqual(h.to_list(), ["x", "y"])
        h.delete_val("x")
        self.assertEqual(len(h), 1)

    def test_circular_delivery_loop(self):
        c = CircularLinkedList(["depot", "A", "B"])
        self.assertEqual(c.to_list(), ["depot", "A", "B"])
        c.rotate(1)
        self.assertEqual(c.to_list(), ["A", "B", "depot"])
        c.delete_val("B")
        self.assertEqual(c.to_list(), ["A", "depot"])
        self.assertEqual(len(c), 2)

class TestPolynomial(unittest.TestCase):
    def test_add_same_order(self):
        p = Polynomial([(3, 2), (2, 1), (1, 0)])
        q = Polynomial([(1, 2), (4, 0)])
        r = p.add(q)
        self.assertEqual(r.evaluate(2), 4 * 4 + 2 * 2 + 5)
        self.assertEqual(r.terms(), [(4, 2), (2, 1), (5, 0)])

    def test_multiply(self):
        p = Polynomial([(2, 1), (1, 0)])
        q = Polynomial([(3, 2), (1, 1)])
        r = p.multiply(q)
        self.assertAlmostEqual(r.evaluate(2), 5 * 14)
        self.assertEqual(r.terms()[0], (6, 3))

    def test_cancellation(self):
        p = Polynomial([(5, 3), (2, 1)])
        q = Polynomial([(-5, 3), (1, 2)])
        r = p.add(q)
        self.assertEqual(r.terms(), [(1, 2), (2, 1)])

    def test_cost_model_display(self):
        p = Polynomial([(0.5, 2), (2, 1), (100, 0)])
        self.assertEqual(p.evaluate(10), 0.5 * 100 + 20 + 100)
        self.assertEqual(p.to_display(), "0.5x^2 + 2x + 100")

class TestDSU(unittest.TestCase):
    def test_union_find_rank(self):
        d = DSU(6)
        d.union(0, 1); d.union(1, 2)
        d.union(3, 4)
        self.assertTrue(d.connected(0, 2))
        self.assertFalse(d.connected(2, 3))
        self.assertEqual(d.n_components, 3)
        d.union(2, 3)
        self.assertEqual(d.n_components, 2)
        comps = d.components()
        self.assertEqual(comps[0], [0, 1, 2, 3, 4])
        self.assertEqual(comps[1], [5])

class TestTrie(unittest.TestCase):
    def test_insert_search_delete(self):
        t = Trie()
        for w in ["Central Station", "Central Mall", "City Park", "Court"]:
            t.insert(w)
        self.assertTrue(t.search("Central Mall"))
        self.assertFalse(t.search("Central"))
        self.assertEqual(sorted(t.autocomplete("central", limit=10)),
                         ["Central Mall", "Central Station"])
        self.assertEqual(t.autocomplete("c", limit=2), sorted(
            ["Central Mall", "Central Station", "City Park", "Court"])[:2])
        self.assertTrue(t.delete("Court"))
        self.assertFalse(t.search("Court"))
        self.assertTrue(t.startswith("Central"))
        self.assertFalse(t.delete("Nope"))

def _check_sorted(a):
    return all(a[i - 1] <= a[i] for i in range(1, len(a)))

class TestSorting(unittest.TestCase):
    def _cases(self):
        return [[], [1], [3, 1], [5, 2, 9, 1, 5], random.sample(range(100), 40),
                [1] * 5, [9, 8, 7, 6, 5, 4]]

    def _run_each(self, fn):
        for data in self._cases():
            self.assertTrue(_check_sorted(fn(data)), "failed on %s" % (data,))

    def test_all_sorts_sorted_correctly(self):
        self._run_each(shell_sort)
        self._run_each(quick_sort)
        self._run_each(merge_sort)
        self._run_each(heap_sort)
        self._run_each(counting_sort)

    def test_stability(self):
        """Stable sorts must keep pairs ordered by input arrival for ties."""
        keyed = [(2, "a"), (1, "b"), (2, "c"), (1, "d"), (2, "e")]
        stable_out = merge_sort(keyed)
        ties = [tag for k, tag in stable_out if k == 2]
        self.assertEqual(ties, ["a", "c", "e"])
        counting = counting_sort(keyed, key=lambda p: p[0])
        ties_c = [tag for k, tag in counting if k == 2]
        self.assertEqual(ties_c, ["a", "c", "e"])
        qs = quick_sort(keyed)
        self.assertTrue(_check_sorted([k for k, _ in qs]))
        self.assertTrue(_check_sorted([k for k, _ in shell_sort(keyed)]))
        self.assertTrue(_check_sorted([k for k, _ in heap_sort(keyed)]))

    def test_benchmark_counts(self):
        arr = random.sample(range(50), 30)
        res = benchmark_all(arr)
        self.assertEqual(len(res), 5)
        for r in res:
            self.assertTrue(r["sorted_ok"])
            self.assertGreaterEqual(r["comparisons"], 0)
        self.assertEqual(res[2]["algo"], "merge")

    def test_external_sort(self):
        arr = random.sample(range(100), 17)
        trace = external_sort(arr, chunk_size=4)
        self.assertEqual(trace["final"], sorted(arr))
        self.assertGreater(trace["passes"], 0)

    def test_searches(self):
        arr = [1, 4, 7, 9, 15, 22, 30]
        self.assertEqual(binary_search(arr, 9), (3, 1))
        self.assertEqual(binary_search(arr, 10), (-1, 3))
        self.assertEqual(linear_search(arr, 15), (4, 5))
        self.assertEqual(linear_search(arr, 99)[0], -1)

    def test_merge_sort_orders(self):
        orders = [{"priority": 2, "weight": 1}, {"priority": 1, "weight": 5},
                  {"priority": 1, "weight": 3}, {"priority": 3, "weight": 9}]
        out = merge_sort_orders(orders)
        self.assertEqual([o["priority"] for o in out], [1, 1, 2, 3])
        self.assertEqual(out[0]["weight"], 5)

class TestHashing(unittest.TestCase):
    def test_hash_functions(self):
        self.assertEqual(hash_division(97, 11), 97 % 11)
        v = hash_mid_square(42, 100)
        self.assertTrue(0 <= v < 100)

        self.assertTrue(0 <= hash_folding(12345, 100, chunk=2) < 100)
