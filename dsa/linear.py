"""
dsa/linear.py -- Unit-I linear data structures, written from scratch.

Used BY the app for:
  * DynStack          -> UNDO stack in app.Store, path reconstruction, backtracking
  * TwoStacks/NStacks -> "multiple stacks in one array" demo (viva point)
  * MinHeapPQ         -> Dijkstra, Prim, dispatch priority queue, k-way merge
  * SortedListPQ      -> alternative PQ (sorted linked list) with documented O()
  * CircularQueue     -> round-robin driver assignment
  * DequeIR/DequeOR   -> input-restricted / output-restricted deque demo
"""

class DynStack:
    """Dynamic stack over a plain Python list.

    Grows by *doubling* when full, halves when <= 1/4 full (amortised O(1) push/pop).
    Time: push/pop/peek O(1) amortised; space O(n).
    """

    def __init__(self):
        self._a = []
        self._n = 0

    def __len__(self):
        return self._n

    def is_empty(self):
        return self._n == 0

    def _resize(self, cap):
        """Copy the n live items into a new array of size cap (O(n))."""
        new = [None] * cap
        for i in range(self._n):
            new[i] = self._a[i]
        self._a = new

    def push(self, x):
        if self._n == len(self._a):
            cap = 1 if self._n == 0 else len(self._a) * 2
            self._resize(cap)
        self._a[self._n] = x
        self._n += 1

    def pop(self):
        if self.is_empty():
            raise IndexError("pop from empty stack")
        self._n -= 1
        x = self._a[self._n]
        self._a[self._n] = None

        if len(self._a) >= 8 and self._n <= len(self._a) // 4:
            self._resize(max(8, len(self._a) // 2))
        return x

    def peek(self):
        if self.is_empty():
            raise IndexError("peek from empty stack")
        return self._a[self._n - 1]

    def items(self):
        """bottom..top snapshot (for UI / JSON)."""
        return [self._a[i] for i in range(self._n)]

class TwoStacks:
    """Two stacks sharing ONE array: stack 0 grows left->right, stack 1 grows right->left.
    Push when combined total < capacity never needs shifting. O(1) per op, space O(cap)."""

    def __init__(self, capacity=16):
        self._a = [None] * capacity
        self._cap = capacity
        self._top0 = -1
        self._top1 = capacity

    def push0(self, x):
        if self._top0 + 1 == self._top1:
            raise OverflowError("stack array full")
        self._top0 += 1
        self._a[self._top0] = x

    def push1(self, x):
        if self._top1 - 1 == self._top0:
            raise OverflowError("stack array full")
        self._top1 -= 1
        self._a[self._top1] = x

    def pop0(self):
        if self._top0 == -1:
            raise IndexError("stack0 empty")
        x = self._a[self._top0]
        self._top0 -= 1
        return x

    def pop1(self):
        if self._top1 == self._cap:
            raise IndexError("stack1 empty")
        x = self._a[self._top1]
        self._top1 += 1
        return x

    def sizes(self):
        return (self._top0 + 1, self._cap - self._top1)

class NStacksOneArray:
    """k stacks in ONE array, reallocated via a linked FREE LIST chain.

    a[i]        = value at cell i
    next_free[i]= next free cell (or -1) forming the free list
    tops[k]     = top cell of stack k (or -1)
    Time: O(1) push/pop per stack. Space O(k + cap). No per-stack resizing needed.
    """

    def __init__(self, k, capacity):
        if k < 1 or capacity < k:
            raise ValueError("need capacity >= stacks")
        self._k, self._cap = k, capacity
        self.a = [None] * capacity
        self.top = [-1] * k
        self.free = 0
        self._nfree = capacity
        self.nxt = [i + 1 for i in range(capacity)]
        self.nxt[capacity - 1] = -1

    def push(self, k, x):
        if self._nfree == 0:
            raise OverflowError("no free cell")
        i = self.free
        self.free = self.nxt[i]
        self._nfree -= 1
        self.a[i] = x
        self.nxt[i] = self.top[k]
        self.top[k] = i

    def pop(self, k):
        if self.top[k] == -1:
            raise IndexError("stack %d empty" % k)
        i = self.top[k]
        x = self.a[i]
        self.top[k] = self.nxt[i]
        self.a[i] = None
        self.nxt[i] = self.free
        self.free = i
        self._nfree += 1
        return x

class MinHeapPQ:
    """Array min-heap priority queue (binary heap, 0-indexed children 2i+1, 2i+2).

    push O(log n) with sift-up; pop-min O(log n) with sift-down; peek O(1).
    Entries may be (key, value) pairs; comparisons are countable for the lab.
    """

    def __init__(self):
        self._h = []
        self.comparisons = 0

    def __len__(self):
        return len(self._h)

    def is_empty(self):
        return len(self._h) == 0

    @staticmethod
    def _l(i):
        return 2 * i + 1

    @staticmethod