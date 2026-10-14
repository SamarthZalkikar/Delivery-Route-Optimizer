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
