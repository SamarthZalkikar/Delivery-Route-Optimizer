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
