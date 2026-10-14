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

def _is_sorted(a):
    for i in range(1, len(a)):
        if a[i - 1] > a[i]:
            return False
    return True

def external_sort(arr, chunk_size=4):
    """Chunked k-way merge, i.e. what a disk-bound external sort does.

    Pass 0: split into ceil(n/chunk) runs; sort EACH RUN in memory (merge sort).
    Pass 1..k: merge `fan_in` runs at a time into bigger runs using MinHeapPQ.
    Returns trace of runs + passes (for the UI panel)."""
    n = len(arr)
    if n <= 1 or chunk_size < 2:
        return {"chunks": [list(arr)], "passes": 0, "final": list(arr),
                "timings": []}
    stash = _stats()
    chunks = []
    for i in range(0, n, chunk_size):
        chunks.append(merge_sort(arr[i:i + chunk_size], stash))
    trace = {"chunks": chunks, "passes": 0, "timings": []}
    runs = chunks
    fan_in = chunk_size
    while len(runs) > 1:
        merged = []
        for i in range(0, len(runs), fan_in):
            group = runs[i:i + fan_in]
            merged.append(_kway_merge(group, stash))
            trace["timings"].append(len(group))
        runs = merged
        trace["passes"] += 1
    trace["final"] = runs[0]
    trace["comparisons_total"] = stash["comparisons"]
    return trace

def _kway_merge(runs, stats=None):
    """MINHEAP k-way merge with (item, run_idx) entries. O(N log k)."""
    s = stats or _stats()
    pq = MinHeapPQ()
    out = []
    heads = [0] * len(runs)
    for r in range(len(runs)):
        if heads[r] < len(runs[r]):
            pq.push(runs[r][heads[r]], r)
            heads[r] += 1
    while not pq.is_empty():
        item, r = pq.pop_min()
        out.append(item)

        if heads[r] < len(runs[r]):
            pq.push(runs[r][heads[r]], r)
            heads[r] += 1
    return out

def linear_search(arr, target):
    """Scan left->right. O(n). Returns (index, steps) or (-1, steps)."""
    steps = 0
    for i in range(len(arr)):
        steps += 1
        if arr[i] == target:
            return i, steps
    return -1, steps

def binary_search(arr, target, pre_sorted=True):
    """Sorted-array halving search. O(log n). Returns (index, steps).

    When pre_sorted is False (default UI doesn't do it), a merge sort runs
    first and that cost is reported via the returned steps tuple."""
    a = arr
    steps = 0
    if not pre_sorted:
        a = merge_sort(arr)
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        steps += 1
        if a[mid] == target:
            return mid, steps
        s_cmp = a[mid] < target
        if s_cmp:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1, steps

def merge_sort_orders(orders):
    """Stable merge sort on order objects by (priority asc, weight desc).
    Returns the sorted list of order records; O(n log n)."""
    return _ms_orders(list(orders))

def _ms_orders(a):
    n = len(a)
    if n <= 1:
        return a
    mid = n // 2
    left = _ms_orders(a[:mid])
    right = _ms_orders(a[mid:])
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        li, rj = left[i], right[j]
        lp, rp = li["priority"], rj["priority"]
        lc = -li["weight"]
        rc = -rj["weight"]
        if (lp, lc) <= (rp, rc):
            out.append(li)
            i += 1
        else:
            out.append(rj)
            j += 1
    while i < len(left):
        out.append(left[i])
        i += 1
    while j < len(right):
        out.append(right[j])
        j += 1
    return out
