"""
dsa/hashing.py -- Unit-IV hash tables (chaining + open addressing) and the
three classic hash functions (division, mid-square, folding).

Used BY the app for:
  * order-ID lookup        (/api/orders/<id> demo view,
                            /api/hash-demo?key=)
  * location symbol table  (name -> id)
"""

def hash_division(key, m):
    """Key mod m (prime m for best spread). O(1)."""
    return key % m

def hash_mid_square(key, m):
    """Square the key and lift the MIDDLE digits (base-10) that fit m. O(1)."""
    sq = key * key
    digits = _digits(sq)
    need = len(_digits(m - 1)) if m > 1 else 1
    if len(digits) <= need:
        return sq % m
    mid = len(digits) // 2
    start = mid - need // 2
    start = max(0, start)
    picked = 0
    for k in range(need):
        if start + k < len(digits):
            picked = picked * 10 + digits[start + k]
    return picked % m

def hash_folding(key, m, chunk=3):
    """Split the key's digits into `chunk`-wide groups, ADD them, then mod m. O(d)."""
    digits = _digits(key)
    if not digits:
        return key % m
    parts, i = [], len(digits)
    while i > 0:
        j = i - chunk
        val = 0
        for k in range(j, i):
            val = val * 10 + digits[k]
        parts.append(val)
        i = j
    total = 0
    for p in parts:
        total += p
    return total % m

def _digits(n):
    """List the decimal digits of n = 0.. without strings (plain arithmetic)."""
    if n == 0:
        return [0]
    out = []
    while n > 0:
        out.append(n % 10)
        n //= 10
    out.reverse()
    return out

class _ChainNode:
    __slots__ = ("key", "value", "nxt")

    def __init__(self, key, value, nxt=None):
        self.key = key
        self.value = value
        self.nxt = nxt

class HashTableChaining:
    """Separate chaining hash table. Each bucket is a SINGLY LINKED LIST.

    insert/lookup/delete: O(1) expected, O(n) worst (all keys in one chain);
    collisions counted every insert that lands on a NON-empty bucket.
    """

    def __init__(self, size=11, hashfn=hash_division):
        self.size = size
        self.hashfn = hashfn
        self.buckets = [None] * size
        self.n_keys = 0
        self.collisions = 0

    def _bucket(self, key):
        return self.hashfn(key, self.size)

    def insert(self, key, value):
        """Head-insert into the chain (classic textbook style). O(1)."""
        b = self._bucket(key)
        node = self.buckets[b]
        if node is not None:
            self.collisions += 1
            cur = node
            while cur:
                if cur.key == key:
                    cur.value = value
                    return
                cur = cur.nxt
        self.buckets[b] = _ChainNode(key, value, self.buckets[b])
        self.n_keys += 1

    def lookup(self, key):
        b = self._bucket(key)
        cur, steps = self.buckets[b], 1
        while cur:
            if cur.key == key:
                return cur.value, steps
            steps += 1
            cur = cur.nxt
        return None, steps

    def delete(self, key):
        b = self._bucket(key)
        prev, cur = None, self.buckets[b]
        while cur:
            if cur.key == key:
                if prev is None:
                    self.buckets[b] = cur.nxt
                else:
                    prev.nxt = cur.nxt
                self.n_keys -= 1
                return True
            prev, cur = cur, cur.nxt
        return False

    def snapshot(self):
        """Buckets as (index, [key,...]) for the UI collision panel."""
        out = []
        for i in range(self.size):
            items, cur = [], self.buckets[i]
            while cur:
                items.append((cur.key, cur.value))
                cur = cur.nxt
            out.append(items)
        return out

class HashTableOpen:
    """Open addressing in a plain array. probe_fn(index, attempt, size)->offset.

    resolution='linear'    : probe i+1, i+2 ...          (primary clustering)
    resolution='quadratic' : probe i+1^2, i+2^2 ...      (secondary clustering)
    resolution='double'    : probe i + attempt*h2(key)   (double hashing)
    Each probe = one comparison: lookup returns (value, steps).
    Deleted slots carry a TOMBSTONE so chains under deletion stay findable.
    """

    def __init__(self, size=11, resolution="linear", hashfn=hash_division):
        self.size = size
        self.resolution = resolution
        self.hashfn = hashfn
        self.slots = [None] * size
        self.n_keys = 0
        self.collisions = 0

    def _home(self, key):
        return self.hashfn(key, self.size)

    def _h2(self, key):
        """Secondary hash for double hashing (any odd number < size, != 1..0)."""
        return 1 + (self.hashfn(key, self.size - 1))

    def _probe(self, key, attempt):
        h = self._home(key)
        if self.resolution == "linear":
            return (h + attempt) % self.size
        if self.resolution == "quadratic":
            return (h + attempt * attempt) % self.size

        return (h + attempt * self._h2(key)) % self.size

    def insert(self, key, value):
        """First-fit probe; TOMBSTONE slots are reusable. Fails when full. O(size)."""
        if self.size == self.n_keys + self._tombs():
            self._grow()
        for attempt in range(self.size):
            s = self._probe(key, attempt)
            cell = self.slots[s]
            if cell is None or cell == ("_TOMB_", None):
                self.slots[s] = (key, value)
                self.n_keys += 1
                self.collisions += attempt
                return attempt
            if cell[0] == key:
                self.slots[s] = (key, value)
                return attempt
        self._grow()
        return self.insert(key, value)

    def lookup(self, key):
        steps = 0
        for attempt in range(self.size):
            s = self._probe(key, attempt)
            steps += 1
            cell = self.slots[s]
            if cell is None:
                return None, steps
            if cell != ("_TOMB_", None) and cell[0] == key:
                return cell[1], steps
        return None, steps

    def delete(self, key):
        for attempt in range(self.size):
            s = self._probe(key, attempt)
            cell = self.slots[s]
            if cell is None:
                return False
            if cell != ("_TOMB_", None) and cell[0] == key:
                self.slots[s] = ("_TOMB_", None)
                self.n_keys -= 1
                return True
        return False

    def _tombs(self):
        c = 0
        for cell in self.slots:
            if cell == ("_TOMB_", None):
                c += 1
        return c

    def _grow(self):
        """Rehash everything into a bigger table (next odd prime-ish). O(n)."""
        old = self.slots
        self.size = self.size * 2 + 1
        self.slots = [None] * self.size
        self.n_keys = 0
        for cell in old:
            if cell is not None and cell != ("_TOMB_", None):
                self.insert(cell[0], cell[1])

    def snapshot(self):
        """Bucket view for UI: (index, key-or-'TOMB'/'EMPTY-never?', value)."""
        out = []
        for i in range(self.size):
            cell = self.slots[i]
            if cell is None:
                out.append((i, None, None))
            elif cell == ("_TOMB_", None):
                out.append((i, "_TOMB_", None))
            else:
                out.append((i, cell[0], cell[1]))
        return out
