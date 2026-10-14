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
    def _r(i):
        return 2 * i + 2

    @staticmethod
    def _p(i):
        return (i - 1) // 2

    def push(self, key, value=None):
        item = key if value is None else [key, value]
        self._h.append(item)
        i = len(self._h) - 1
        while i > 0:
            p = self._p(i)
            if self._less(self._h[i], self._h[p]):
                self._h[i], self._h[p] = self._h[p], self._h[i]
                i = p
            else:
                break

    def _less(self, x, y):
        """Compare two entries on KEY only; exact key ties keep insert order
        (values are never compared, so dict-valued entries cannot explode)."""
        self.comparisons += 1
        if type(x) is list and type(y) is list:
            return x[0] < y[0]
        return x < y

    def pop_min(self):
        if self.is_empty():
            raise IndexError("pop from empty heap")
        top = self._h[0]
        last = self._h.pop()
        if self._h:
            self._h[0] = last
            self._sift_down(0, len(self._h))
        return top if type(top) is not list else top

    def _sift_down(self, i, n):
        while True:
            l, r = self._l(i), self._r(i)
            best = i
            if l < n and self._less(self._h[l], self._h[best]):
                best = l
            if r < n and self._less(self._h[r], self._h[best]):
                best = r
            if best == i:
                return
            self._h[i], self._h[best] = self._h[best], self._h[i]
            i = best

    def peek(self):
        if self.is_empty():
            return None
        return self._h[0]

class SortedListPQ:
    """Priority queue over a SORTED SINGLY LINKED LIST (ascending by key).

    insert O(n) walk + O(1) unlink-in; pop_min O(1); peek O(1). Space O(n).
    Contrast with MinHeapPQ (push O(log n), pop O(log n)); hand-wavy alternative.
    """

    class _Node:
        __slots__ = ("key", "val", "nxt")

        def __init__(self, key, val, nxt=None):
            self.key = key
            self.val = val
            self.nxt = nxt

    def __init__(self):
        self._head = None
        self._n = 0
        self.comparisons = 0

    def push(self, key, val=None):
        self._n += 1
        if self._head is None:
            self._head = self._Node(key, val)
            return

        if key < self._head.key:
            self._head = self._Node(key, val, self._head)
            return
        cur = self._head
        while cur.nxt is not None:
            self.comparisons += 1
            if key < cur.nxt.key:
                break
            cur = cur.nxt
        cur.nxt = self._Node(key, val, cur.nxt)

    def pop_min(self):
        if self._head is None:
            raise IndexError("pop from empty PQ")
        node, self._head = self._head, self._head.nxt
        self._n -= 1
        return node.key if node.val is None else (node.key, node.val)

    def peek(self):
        if self._head is None:
            return None
        return self._head.key if self._head.val is None else (self._head.key, self._head.val)

    def __len__(self):
        return self._n

    def is_empty(self):
        return self._head is None

class CircularQueue:
    """Fixed-capacity circular (ring) queue -- array indexes wrap with %.

    front O(1), enqueue/rear O(1); used for DRIVER ROUND-ROBIN and BFS fringe.
    Full condition: (rear+1) % cap == front (one wasted slot keeps it simple).
    """

    def __init__(self, capacity=16):
        self.cap = max(2, capacity)
        self._a = [None] * self.cap
        self.front = 0
        self.rear = 0

    def is_empty(self):
        return self.front == self.rear

    def is_full(self):
        return (self.rear + 1) % self.cap == self.front

    def enqueue(self, item):
        if self.is_full():
            raise OverflowError("circular queue full (cap=%d)" % (self.cap - 1))
        self._a[self.rear] = item
        self.rear = (self.rear + 1) % self.cap

    def dequeue(self):
        if self.is_empty():
            raise IndexError("circular queue empty")
        item = self._a[self.front]
        self._a[self.front] = None
        self.front = (self.front + 1) % self.cap
        return item

    def peek(self):
        if self.is_empty():
            return None
        return self._a[self.front]

    def snapshot(self):
        """Items currently in queue front->rear (for UI)."""
        out, i = [], self.front
        while i != self.rear:
            out.append(self._a[i])
            i = (i + 1) % self.cap
        return out

    def __len__(self):
        c = self.rear - self.front
        return c if c >= 0 else c + self.cap

class ArrayDeque:
    """Array-backed deque with blocked-ends index arithmetic; superset of queue+stack.

    push_front / push_back / pop_front / pop_back all O(1) amortised
    (plain-list DoublingArray {grow 2x at back, shrink <1/4} reused).
    """

    def __init__(self):
        self._a = []
        self._front = 0
        self._n = 0

    def _live(self, i):
        return (self._front + i) % len(self._a)

    def push_back(self, x):
        self._push_tail(x)

    def push_front(self, x):
        self._push_head(x)

    def pop_back(self):
        return self._pop_tail()

    def pop_front(self):
        return self._pop_head()

    def _push_tail(self, x):
        if self._n == len(self._a):
            self._grow_back(True, x)
        else:
            self._a[self._live(self._n)] = x
        self._n += 1

    def _push_head(self, x):
        if self._n == len(self._a):
            self._grow_back(True, None)
        self._front = (self._front - 1) % len(self._a)
        self._a[self._front] = x
        self._n += 1

    def _pop_head(self):
        if self._n == 0:
            raise IndexError("pop from empty deque")
        x = self._a[self._front]
        self._a[self._front] = None
        self._front = (self._front + 1) % len(self._a)
        self._n -= 1
        self._maybe_shrink()
        return x

    def _pop_tail(self):
        if self._n == 0:
            raise IndexError("pop from empty deque")
        x = self._a[self._live(self._n - 1)]
        self._a[self._live(self._n - 1)] = None
        self._n -= 1
        self._maybe_shrink()
        return x

    def _grow_back(self, at_back, x):
        new = [None] * (max(8, len(self._a) * 2))
        for i in range(self._n):
            new[i] = self._a[self._live(i)]
        self._a, self._front = new, 0
        if x is not None:
            self._a[self._n] = x

    def _maybe_shrink(self):
        if len(self._a) >= 16 and self._n <= len(self._a) // 4:
            self._grow_back(False, None)

    def __len__(self):
        return self._n

    def is_empty(self):
        return self._n == 0

    def peek_front(self):
        return None if self._n == 0 else self._a[self._front]

    def peek_back(self):
        return None if self._n == 0 else self._a[self._live(self._n - 1)]

class DequeIR:
    """INPUT-RESTRICTED deque: insertions ONLY at the rear; deletions at both ends.

    push_front() is deliberately FORBIDDEN (raises). All other ops match ArrayDeque.
    """

    def __init__(self):
        self._q = ArrayDeque()

    def push_back(self, x):
        self._q.push_back(x)

    def _forbidden(self, op):
        raise TypeError("Input-restricted deque: cannot %s" % op)

    pop_front = property(lambda self: self._q.pop_front)
    pop_back = property(lambda self: self._q.pop_back)

class DequeOR:
    """OUTPUT-RESTRICTED deque: deletions ONLY at the front; insertions at both ends."""

    def __init__(self):
        self._q = ArrayDeque()

    def push_front(self, x):
        self._q.push_front(x)

    def push_back(self, x):
        self._q.push_back(x)

    def pop_front(self):
        return self._q.pop_front()

    def _forbidden(self, op):
        raise TypeError("Output-restricted deque: cannot %s pop from the back" % op)
