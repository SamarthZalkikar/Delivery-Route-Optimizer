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

def heap_sort(arr, stats=None):
    """Build max-heap with sift-down, then pop root to the end. O(n log n)."""
    a = list(arr)
    s = stats or _stats()
    n = len(a)
    for i in range(n // 2 - 1, -1, -1):
        _sift(a, i, n, s)
    for end in range(n - 1, 0, -1):
        _swap(a, 0, end, s)
        _sift(a, 0, end, s)
    return a

def _sift(a, i, n, s):
    """MAX-heap sift-down over a[:n] (root must dominate for sort ascending)."""
    while True:
        l, r, big = 2 * i + 1, 2 * i + 2, i
        s["comparisons"] += 1
        if l < n and a[l] > a[big]:
            big = l
        s["comparisons"] += 1
        if r < n and a[r] > a[big]:
            big = r
        if big == i:
            return
        _swap(a, i, big, s)
        i = big

def counting_sort(arr, stats=None, key=None):
    """STABLE counting sort (expects small non-negative int keys, range <= 10k).

    Count occurrences, PREFIX-SUM the counts, then refill from the RIGHT,
    which is what makes it stable. O(n + k) time, O(k) space.
    `key` optionally maps each record to its integer sort key (default: id).
    """
    a = list(arr)
    s = stats or _stats()
    if not a:
        return a
    kf = key if key is not None else (lambda v: v)
    keys = [kf(v) for v in a]
    k = keys[0]
    for v in keys:
        s["comparisons"] += 1
        if v > k:
            k = v
    counts = [0] * (k + 1)
    for v in keys:
        counts[v] += 1
    for i in range(1, k + 1):
        counts[i] += counts[i - 1]
    s["moves"] += k + 1
    out = [0] * len(a)
    for i in range(len(a) - 1, -1, -1):
        counts[keys[i]] -= 1
        out[counts[keys[i]]] = a[i]
        s["moves"] += 1
    return out

SORT_ALGOS = {
    "shell": {"fn": shell_sort, "stable": False, "best": "O(n log n)",
              "avg": "O(n^1.3)", "worst": "O(n^2)"},
    "quick": {"fn": quick_sort, "stable": False, "best": "O(n log n)",
              "avg": "O(n log n)", "worst": "O(n^2)"},
    "merge": {"fn": merge_sort, "stable": True, "best": "O(n log n)",
              "avg": "O(n log n)", "worst": "O(n log n)"},
    "heap": {"fn": heap_sort, "stable": False, "best": "O(n log n)",
             "avg": "O(n log n)", "worst": "O(n log n)"},
    "counting": {"fn": counting_sort, "stable": True, "best": "O(n+k)",
                 "avg": "O(n+k)", "worst": "O(n+k)"},
}

def benchmark_all(arr):
    """Run every sort on a COPY of arr (sort changes never bleed into each other);
    returns [{'algo','comparisons','swaps','moves','stable','ms'}...]"""
    import time
    out = []
    for name, meta in SORT_ALGOS.items():
        stash = _stats()
        t0 = time.perf_counter()
        res = meta["fn"](arr, stash)
        ms = (time.perf_counter() - t0) * 1000.0
        out.append({
            "algo": name,
            "comparisons": stash["comparisons"],
            "swaps": stash["swaps"],
            "moves": stash["moves"],
            "stable": meta["stable"],
            "best": meta["best"],
            "avg": meta["avg"],
            "worst": meta["worst"],
            "ms": round(ms, 3),
            "sorted_ok": _is_sorted(res),
        })
    return out
