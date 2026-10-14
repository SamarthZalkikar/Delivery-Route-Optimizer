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

class DoublyLinkedList:
    """DLL with head+tail. push_front/back, insert_after, delete_node O(1);
    search O(n). Used for order-activity history where we walk backwards."""

    def __init__(self, vals=()):
        self.head = None
        self.tail = None
        self.n = 0
        for v in vals:
            self.push_back(v)

    def push_front(self, v):
        node = DLNode(v, None, self.head)
        if self.head:
            self.head.prev = node
        else:
            self.tail = node
        self.head = node
        self.n += 1

    def push_back(self, v):
        node = DLNode(v, self.tail, None)
        if self.tail:
            self.tail.nxt = node
        else:
            self.head = node
        self.tail = node
        self.n += 1

    def insert_after(self, node, v):
        new = DLNode(v, node, node.nxt)
        if node.nxt:
            node.nxt.prev = new
        else:
            self.tail = new
        node.nxt = new
        self.n += 1

    def delete_node(self, node):
        if node.prev:
            node.prev.nxt = node.nxt
        else:
            self.head = node.nxt
        if node.nxt:
            node.nxt.prev = node.prev
        else:
            self.tail = node.prev
        self.n -= 1

    def to_list(self):
        out, cur = [], self.head
        while cur:
            out.append(cur.val)
            cur = cur.nxt
        return out

    def to_list_reverse(self):
        out, cur = [], self.tail
        while cur:
            out.append(cur.val)
            cur = cur.prev
        return out

    def __len__(self):
        return self.n

class HeaderNode:
    """Header (dummy) node variant -- header lists carry a dedicated head cell
    that never holds data (optionally a count). Simplifies edge-case code and
    is the classic sparse-matrix row struct."""
    __slots__ = ("count", "nxt")

    def __init__(self):
        self.count = 0
        self.nxt = None

class HeaderLinkedList:
    """Header linked list (GROUND variant: header holds no info) with an O(1)
    counter. push_back O(1), delete_val O(n), to_list O(n)."""

    def __init__(self):
        self.header = HeaderNode()
        self._tail = self.header

    def push_back(self, v):
        node = SLNode(v)
        self._tail.nxt = node
        self._tail = node
        self.header.count += 1

    def delete_val(self, v):
        """Unlink first match; prev pointer tracing from the header cell."""
        prev, cur = self.header, self.header.nxt
        while cur:
            if cur.val == v:
                prev.nxt = cur.nxt
                if cur is self._tail:
                    self._tail = prev
                self.header.count -= 1
                return True
            prev, cur = cur, cur.nxt
        return False

    def __len__(self):
        return self.header.count

    def to_list(self):
        return [node.val for node in iter_list(self.header.nxt)]

def iter_list(start):
    cur = start
    while cur:
        yield cur
        cur = cur.nxt

class CLNode:
    """Circular linked-list node (same SLNode shape, but .nxt cycles)."""
    __slots__ = ("val", "nxt")

    def __init__(self, val, nxt=None):
        self.val = val
        self.nxt = nxt

class CircularLinkedList:
    """Singly-linked CIRCULAR list (tail.nxt loops back to head).

    Used as THE DELIVERY LOOP: route stops joined into a ring, so the driver
    can keep cycling the route forever. O(1) insert_front/back with tail ptr;
    to_list walks exactly n nodes then stops (no infinite loop)."""

    def __init__(self, vals=()):
        self.tail = None
        self.n = 0
        for v in vals:
            self.push_back(v)

    def push_back(self, v):
        node = CLNode(v)
        if self.tail is None:
            node.nxt = node
            self.tail = node
        else:
            node.nxt = self.tail.nxt
            self.tail.nxt = node
            self.tail = node
        self.n += 1

    def push_front(self, v):
        node = CLNode(v)
        if self.tail is None:
            node.nxt = node
            self.tail = node
        else:
            node.nxt = self.tail.nxt
            self.tail.nxt = node
        self.n += 1

    def rotate(self, k=1):
        """Advance head k positions along the ring (like turning the route wheel)."""
        if self.n == 0:
            return
        for _ in range(k % self.n):
            self.tail = self.tail.nxt

    def delete_val(self, v):
        """Remove first node with val by walking the ring once. O(n)."""
        if self.n == 0:
            return False
        cur = self.tail.nxt
        prev = self.tail
        for _ in range(self.n):
            if cur.val == v:
                if cur is prev:
                    self.tail = None
                else:
                    prev.nxt = cur.nxt
                    if cur is self.tail:
                        self.tail = prev
                self.n -= 1
                return True
            prev, cur = cur, cur.nxt
        return False

    def to_list(self):
        out = []
        if self.n == 0:
            return out
        cur = self.tail.nxt
        for _ in range(self.n):
            out.append(cur.val)
            cur = cur.nxt
        return out

    def __len__(self):
        return self.n

    def __iter__(self):
        v = self.to_list()
        for x in v:
            yield x

class PolyTerm:
    """One linked-list cell of a polynomial: coeff * x^exp, exp >= 0, coeff != 0."""
    __slots__ = ("coeff", "exp", "nxt")

    def __init__(self, coeff, exp, nxt=None):
        self.coeff = coeff
        self.exp = exp
        self.nxt = nxt

class Polynomial:
    """Sparse polynomial as a singly linked list, kept sorted by DESCENDING exp
    (insertion sorts by exponent so no list.sort is needed).

    add O(m+n), multiply O(m*n) with merge-normalisation, evaluate O(m).
    Terms with zero net coefficient are dropped (e.g. x*x - x*x).
    Used by the app as the transport COST MODEL: cost(d) = a*d^2 + b*d + c.
    """

    def __init__(self, terms=()):
        self.head = None
        self.n_terms = 0
        for c, e in terms:
            self.add_term(float(c), int(e))

    def add_term(self, coeff, exp):
        """Insert / accumulate a term in descending-exponent order. O(m)."""
        if coeff == 0:
            return
        if self.head is None or exp > self.head.exp:
            self.head = PolyTerm(coeff, exp, self.head)
            self.n_terms += 1
            return
        prev, cur = None, self.head
        while cur is not None and cur.exp > exp:
            prev, cur = cur, cur.nxt
        if cur is not None and cur.exp == exp:
            cur.coeff += coeff
            if cur.coeff == 0:
                if prev is None:
                    self.head = cur.nxt
                else:
                    prev.nxt = cur.nxt
                self.n_terms -= 1
        else:
            new = PolyTerm(coeff, exp, cur)
            if prev is None:
                self.head = new
            else:
                prev.nxt = new
            self.n_terms += 1

    def add(self, other):
        """Term-wise addition: walk both sorted lists once. O(m+n)."""
        result = Polynomial()
        pa, pb = self.head, other.head
        while pa or pb:
            if pb is None or (pa and pa.exp > pb.exp):
                result.add_term(pa.coeff, pa.exp)
                pa = pa.nxt
            elif pa is None or pb.exp > pa.exp:
                result.add_term(pb.coeff, pb.exp)
                pb = pb.nxt
            else:
                s = pa.coeff + pb.coeff
                if s != 0:
                    result.add_term(s, pa.exp)
                pa, pb = pa.nxt, pb.nxt
        return result

    def multiply(self, other):
        """Every term of self * every term of other; add_term keeps order. O(m*n*k)."""
        result = Polynomial()
        pa = self.head
        while pa:
            pb = other.head
            while pb:
                result.add_term(pa.coeff * pb.coeff, pa.exp + pb.exp)
                pb = pb.nxt
            pa = pa.nxt
        return result

    def evaluate(self, x):
        """Straightforward pow-based evaluation (viva clarity). O(m)."""
        total, cur = 0.0, self.head
        while cur:
            p = 1.0
            for _ in range(cur.exp):
                p *= x
            total += cur.coeff * p
            cur = cur.nxt
        return total

    def terms(self):
        out, cur = [], self.head
        while cur:
            out.append((cur.coeff, cur.exp))
            cur = cur.nxt
        return out

    def to_display(self):
        """'3.0x^2 + 2.0x + 1.0' style string (for the UI cost panel)."""
        parts = []
        for c, e in self.terms():
            cs = ("%g" % c)
            if e == 0:
                parts.append(cs)
            elif e == 1:
                parts.append("%sx" % cs if c != 1 else "x")
            else:
                parts.append(("%sx^%d" % (cs, e)) if c != 1 else ("x^%d" % e))
        return " + ".join(parts).replace(" + -", " - ")
