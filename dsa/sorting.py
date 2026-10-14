"""
dsa/sorting.py -- Unit-IV sorts (Shell/Quick/Merge/Heap/Counting), external
sort simulation, and linear/binary search. Every sort is hand-written with
comparison counters; list.sort()/sorted() are never used.

Stability notes:
  * Shell  -> UNSTABLE (distant hops)
  * Quick  -> UNSTABLE (far swaps)  [textbook Lomuto partition)
  * Merge  -> STABLE  (ties keep left-first order: `<=` in the final merge)
  * Heap   -> UNSTABLE (sift-down swaps over distance)
  * Count  -> STABLE  (preserve input order per bucket when refilling)
"""

from dsa.linear import MinHeapPQ

def _stats():
    return {"comparisons": 0, "swaps": 0, "moves": 0}

def shell_sort(arr, stats=None):
    """gapped insertion sort, gap halves each pass (Shell's original, 1959). O(n^1.5)-ish"""
    a = list(arr)
    s = stats or _stats()
    n = len(a)
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            temp = a[i]
            j = i
            while j >= gap:
                s["comparisons"] += 1
                if a[j - gap] > temp:
                    a[j] = a[j - gap]
                    j -= gap
                else:
                    break
            a[j] = temp
            s["moves"] += 1
        gap //= 2
    return a

def quick_sort(arr, stats=None):
    """In-place recursive Lomuto partition; median-of-three pivot. O(n log n) avg."""
    a = list(arr)
    s = stats or _stats()
    _quick(a, 0, len(a) - 1, s)
    return a

def _quick(a, lo, hi, s):
    while lo < hi:
        p = _partition(a, lo, hi, s)
        _quick(a, lo, p - 1, s)
        lo = p + 1

def _partition(a, lo, hi, s):
    """Median-of-three pivot placed at hi, then Lomuto one-way partition."""
    mid = (lo + hi) // 2
    s["comparisons"] += 1
    if a[mid] < a[lo]:
        _swap(a, mid, lo, s)
    s["comparisons"] += 1
    if a[hi] < a[mid]:
        _swap(a, hi, mid, s)
        s["comparisons"] += 1
        if a[hi] < a[lo]:
            _swap(a, hi, lo, s)
    else:
        s["comparisons"] += 1
        if a[hi] < a[lo]:
            _swap(a, hi, lo, s)
    pivot = a[hi]
    i = lo
    for j in range(lo, hi):
        s["comparisons"] += 1
        if a[j] <= pivot:
            _swap(a, i, j, s)
            i += 1
    _swap(a, i, hi, s)
    return i

def _swap(a, i, j, s):
    if i != j:
        a[i], a[j] = a[j], a[i]
        s["swaps"] += 1

class _MergeBuf:
    """Merge-sort scratch, plain arrays only."""
    pass

def merge_sort(arr, stats=None):
    """STABLE top-down merge sort. O(n log n) time, O(n) extra space."""
    a = list(arr)
    s = stats or _stats()
    return _ms(a, s)

def _ms(a, s):
    n = len(a)
    if n <= 1:
        return a
    mid = n // 2
    left = _ms(a[:mid], s)
    right = _ms(a[mid:], s)
    return _merge(left, right, s)

def _merge(left, right, s):
    """Two-finger merge; `<=` keeps ties from LEFT first (this is what makes
    merge sort stable). O(len(left)+len(right))."""
    out = []
    i = j = 0
    while i < len(left) and j < len(right):
        s["comparisons"] += 1
        if left[i] <= right[j]:
            out.append(left[i])
            i += 1
        else:
            out.append(right[j])
            j += 1
    while i < len(left):
        out.append(left[i])
        i += 1
    while j < len(right):
        out.append(right[j])
        j += 1
    s["moves"] += len(left) + len(right)
    return out
