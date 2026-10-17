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

    def test_chaining(self):
        ht = HashTableChaining(size=5)
        for i in range(10):
            ht.insert(i, "v%d" % i)
        self.assertEqual(ht.n_keys, 10)
        self.assertGreater(ht.collisions, 0)
        self.assertEqual(ht.lookup(7)[0], "v7")
        self.assertTrue(ht.delete(7))
        self.assertEqual(ht.lookup(7)[0], None)
        self.assertEqual(ht.n_keys, 9)

    def test_open_addressing_modes(self):
        for mode in ["linear", "quadratic", "double"]:
            ht = HashTableOpen(size=13, resolution=mode)
            for i in range(9):
                ht.insert(i, i * 10)
            self.assertEqual(ht.lookup(5)[0], 50)
            self.assertTrue(ht.delete(5))
            self.assertEqual(ht.lookup(5)[0], None)
            ht.insert(5, -1)
            self.assertEqual(ht.lookup(5)[0], -1)

    def test_open_grow(self):
        ht = HashTableOpen(size=5)
        for i in range(50):
            ht.insert(i, i)
        self.assertEqual(ht.n_keys, 50)
        self.assertEqual(ht.lookup(37)[0], 37)

class TestBST(unittest.TestCase):
    def test_crud_and_traversals(self):
        t = BST()
        for k in [5, 3, 8, 1, 4, 7, 9]:
            t.insert(k, "v%d" % k)
        self.assertEqual(t.inorder(), [1, 3, 4, 5, 7, 8, 9])
        self.assertEqual(t.preorder()[0], 5)
        self.assertEqual(t.postorder()[-1], 5)
        self.assertEqual(t.search(4), "v4")
        self.assertTrue(t.delete(3) and t.delete(5))
        self.assertEqual(t.inorder(), [1, 4, 7, 8, 9])
        self.assertFalse(t.delete(100))
        self.assertEqual(t.height(), 3)

class TestThreadedBST(unittest.TestCase):
    def test_inorder_without_stack(self):
        tt = ThreadedBST()
        for k in [10, 5, 15, 3, 7, 12, 18]:
            tt.insert(k)
        self.assertEqual(tt.inorder_threaded(), [3, 5, 7, 10, 12, 15, 18])
        self.assertEqual(len(tt), 7)

class TestAVL(unittest.TestCase):
    def test_all_rotations_counted(self):
        """LL and RR use 1 rotation each; LR and RL use 2 (double rotation)."""
        a = AVLTree()
        for k in [3, 2, 1]:
            a.insert(k)
        self.assertEqual(a.root.key, 2)
        self.assertEqual(a.rotations, 1)
        a2 = AVLTree()
        for k in [1, 2, 3]:
            a2.insert(k)
        self.assertEqual(a2.root.key, 2)
        self.assertEqual(a2.rotations, 1)
        a3 = AVLTree()
        for k in [3, 1, 2]:
            a3.insert(k)
        self.assertEqual(a3.root.key, 2)
        self.assertEqual(a3.rotations, 2)
        a4 = AVLTree()
        for k in [1, 3, 2]:
            a4.insert(k)
        self.assertEqual(a4.root.key, 2)
        self.assertEqual(a4.rotations, 2)

    def test_delete_and_height_cap(self):
        a = AVLTree()
        for k in range(1, 32):
            a.insert(k)
        self.assertLessEqual(a.height(), 2 * (31 + 1).bit_length())
        self.assertTrue(a.delete(16))
        self.assertFalse(a.delete(999))
        self.assertEqual(a.n, 30)
        self.assertGreaterEqual(a.rotations, 0)

class TestBTree(unittest.TestCase):
    def test_insert_search_delete(self):
        bt = BTree(t=3)
        keys = list(range(1, 51))
        random.shuffle(keys)
        for k in keys:
            bt.insert(k, k * 2)
        self.assertEqual(bt.n, 50)
        for k in keys:
            self.assertEqual(bt.search(k)[0], k * 2)
        all_keys = bt.traversal()
        self.assertEqual(all_keys, sorted(all_keys))
        self.assertEqual(len(all_keys), 50)
        for k in range(1, 21):
            bt.delete(k)
        self.assertEqual(bt.n, 30)
        self.assertEqual(bt.search(5)[0], None)
        self.assertEqual(bt.search(30)[0], 60)

class TestBPlusTree(unittest.TestCase):
    def test_insert_search_range(self):
        bp = BPlusTree(m=4)
        for k in range(1, 41):
            bp.insert(k, k * k)
        self.assertEqual(bp.n, 40)
        self.assertEqual(bp.search(7)[0], 49)
        rng = bp.range_scan(10, 14)
        self.assertEqual([k for k, _ in rng], [10, 11, 12, 13, 14])
        self.assertTrue(all(isinstance(v, int) for _, v in rng))
        levels = bp.snapshot_structure()
        self.assertGreaterEqual(len(levels), 2)

def make_grid_graph():
    """4x4 grid with horizontal+vertical edges, weights = manhattan dist."""
    g = Graph(16)
    def w(a, b):
        (ra, ca), (rb, cb) = divmod(a, 4), divmod(b, 4)
        return abs(ra - rb) + abs(cb - ca)
    for r in range(4):
        for c in range(4):
            u = r * 4 + c
            if c < 3:
                g.add_edge(u, u + 1, w(u, u + 1))
            if r < 3:
                g.add_edge(u, u + 4, w(u, u + 4))
    return g

class TestGraph(unittest.TestCase):
    def test_bfs_dfs(self):
        g = make_grid_graph()
        order, levels = bfs_order(g, 0)
        self.assertEqual(order[0], 0)
        self.assertEqual(len(order), 16)
        self.assertEqual(levels[0], 0)
        self.assertEqual(max(levels), 6)
        d = dfs_order(g, 0)
        self.assertEqual(len(d), 16)
        self.assertEqual(d[0], 0)
        rec = dfs_order(g, 0, recursive=False)
        self.assertEqual(rec, d)

    def test_components(self):
        g = Graph(6)
        g.add_edge(0, 1, 1); g.add_edge(1, 2, 1)
        g.add_edge(3, 4, 1)
        comps, _ = connected_components(g)
        self.assertEqual(len(comps), 3)
        self.assertEqual(comps[0], [0, 1, 2])
        self.assertEqual(comps[2], [5])

    def test_dijkstra(self):
        g = make_grid_graph()
        dist, prev = dijkstra(g, 0)
        self.assertEqual(dist[5], 2)
        self.assertEqual(dist[15], 6)
        path, cost, _ = shortest_path(g, 0, 15)
        self.assertEqual(cost, 6)
        self.assertEqual(path[0], 0)
        self.assertEqual(path[-1], 15)
        self.assertEqual(len(path), 7)

    def test_prim_kruskal_same_cost(self):
        g = make_grid_graph()
        ep, tp = prim_mst(g)
        ek, tk = kruskal_mst(g)
        self.assertEqual(len(ep), 15)
        self.assertEqual(len(ek), 15)
        self.assertAlmostEqual(tp, tk)
        self.assertAlmostEqual(tp, 15)

    def test_all_pairs(self):
        g = make_grid_graph()
        dm, pm = dijkstra_all_pairs(g)
        self.assertEqual(dm[4][5], 1)
        self.assertEqual(dm[0][0], 0)

class TestSparseMatrix(unittest.TestCase):
    def test_linked_rows(self):
        dense = [[0, 7, 0, 0], [0, 0, 0, 0], [0, 0, 0, 3], [1, 0, 9, 0]]
        sm = SparseMatrix.from_dense(dense)
        self.assertEqual(sm.nnz, 4)
        self.assertEqual(sm.get(0, 1), 7)
        self.assertEqual(sm.get(1, 3), None)
        self.assertAlmostEqual(sm.density(), 4 / 16)
        j = sm.as_rows_json()
        d = dict(j)
        self.assertEqual([(c, v) for c, v in d[3]], [(0, 1), (2, 9)])

class TestOptimizer(unittest.TestCase):
    def make_dm(self):
        """4 cities on a line:  0 --1.0-- 1 --2.0-- 2 --3.0-- 3"""
        INF = 9999.0
        dm = [[INF] * 4 for _ in range(4)]
        for i in range(4):
            dm[i][i] = 0.0
        dm[0][1] = dm[1][0] = 1.0
        dm[1][2] = dm[2][1] = 2.0
        dm[2][3] = dm[3][2] = 3.0

        dm[0][2] = dm[2][0] = 2.5
        dm[0][3] = dm[3][0] = 3.5
        dm[1][3] = dm[3][1] = 4.0
        return dm

    def test_exact_matches_brute(self):
        from dsa.sorting import _is_sorted
        dm = self.make_dm()
        ro = RouteOptimizer(dm)
        order, cost, steps = ro.optimize_exact([1, 2, 3], depot=0)

        brute = {
            (dm[0][a] + dm[a][b] + dm[b][c] + dm[c][0], (a, b, c))
            for a, b, c in [(1, 2, 3), (1, 3, 2), (2, 1, 3),
                            (2, 3, 1), (3, 1, 2), (3, 2, 1)]
        }
        best = min(brute)
        self.assertAlmostEqual(cost, best[0])
        self.assertEqual(cost, 9.5)

    def test_exact_refuses_big(self):
        ro = RouteOptimizer(self.make_dm())
        with self.assertRaises(ValueError):
            ro.optimize_exact(list(range(10)), 0)

    def test_heuristic_reasonable(self):
        dm = self.make_dm()
        ro = RouteOptimizer(dm)
        order, cost, _ = ro.optimize_heuristic([1, 2, 3], 0)
        self.assertAlmostEqual(ro.tour_cost(order, 0), cost)
        self.assertLessEqual(cost, 1.2 * 9.5)

    def test_dispatcher_modes(self):
        ro = RouteOptimizer(self.make_dm())
        res = ro.optimize([1, 2], 0, mode="auto")
        self.assertEqual(res["mode"], "exact")
        res2 = ro.optimize([1, 2, 3], 0, mode="heuristic")
        self.assertEqual(res2["algorithm"], "Nearest neighbour + 2-opt")

if __name__ == "__main__":
    unittest.main()
