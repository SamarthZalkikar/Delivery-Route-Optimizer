"""
dsa/linked.py -- Unit-I linked structures, hand-rolled on plain nodes.

Used BY the app for:
  * SinglyLinkedList      -> buckets of the chained hash table
  * HeaderLinkedList       -> sparse road-distance matrix (one SLL header per row)
  * CircularLinkedList     -> the "delivery loop" (stops joined into a ring)
  * DoublyLinkedList       -> order history
  * Polynomial             -> transport-cost model cost(d) = a*d^2 + b*d + c
"""

class SLNode:
    """Singly-linked node. O(1) creation."""
    __slots__ = ("val", "nxt")

    def __init__(self, val, nxt=None):
        self.val = val
        self.nxt = nxt

class SinglyLinkedList:
    """Singly linked list with head/tail pointers.

    push_front O(1), push_back O(1), delete_val O(n), search O(n), reverse O(n).
    Space O(n). Plain nodes; NO list.sort()/deque help involved.
    """

    def __init__(self, vals=()):
        self.head = None
        self.tail = None
        self.n = 0
        for v in vals:
            self.push_back(v)

    def push_front(self, v):
        self.head = SLNode(v, self.head)
        if self.tail is None:
            self.tail = self.head
        self.n += 1

    def push_back(self, v):
        node = SLNode(v)
        if self.head is None:
            self.head = self.tail = node
        else:
            self.tail.nxt = node
            self.tail = node
        self.n += 1

    def search(self, v):
        cur, i = self.head, 0
        while cur:
            if cur.val == v:
                return i
            cur, i = cur.nxt, i + 1
        return -1

    def delete_val(self, v):
        """Delete the FIRST node holding v. Returns True if removed. O(n)."""
        prev, cur = None, self.head
        while cur:
            if cur.val == v:
                if prev is None:
                    self.head = cur.nxt
                else:
                    prev.nxt = cur.nxt
                if cur is self.tail:
                    self.tail = prev
                self.n -= 1
                return True
            prev, cur = cur, cur.nxt
        return False

    def to_list(self):
        out, cur = [], self.head
        while cur:
            out.append(cur.val)
            cur = cur.nxt
        return out

    def __iter__(self):
        cur = self.head
        while cur:
            yield cur.val
            cur = cur.nxt

    def __len__(self):
        return self.n

class DLNode:
    """Doubly-linked node with prev/next pointers."""
    __slots__ = ("val", "prev", "nxt")

    def __init__(self, val, prev=None, nxt=None):
        self.val = val
        self.prev = prev
        self.nxt = nxt
