"""
dsa/dsu.py -- Unit-V Disjoint Set Union (Union-Find).

Used BY the app for:
  * Kruskal's MST (cycle rejection in O(a(n)) amortised)
  * connected components of the road network
Plain integer arrays; NO set() involved anywhere.
"""

class DSU:
    """Disjoint Set with union-by-rank + find-with-path-compression.

    make_set/find O(1) with path compression, union O(a(n)) amortised ≈ O(1).
    Space O(n). parent[i] == i marks a root; rank[] only meaningful at roots.
    """

    def __init__(self, n=0):
        self.parent = []
        self.rank = []
        self.n_components = 0
        for i in range(n):
            self.make_set()

    def make_set(self):
        """Add a fresh singleton set (index = next free id). O(1)."""
        self.parent.append(len(self.parent))
        self.rank.append(0)
        self.n_components += 1
        return len(self.parent) - 1

    def find(self, x):
        """Find representative; compress the path so future finds are O(1)."""
        if x != self.parent[x]:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a, b):
        """Union by rank: shorter tree hangs under the taller root.
        Returns True if two separate sets were actually merged."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[ra] > self.rank[rb]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1
        self.n_components -= 1
        return True

    def connected(self, a, b):
        return self.find(a) == self.find(b)

    def components(self):
        """Group node ids by root WITHOUT dict/set: label scan + buckets.
        O(n * a(n)). Returned sorted by smallest member (insertion sort)."""
        roots = [self.find(i) for i in range(len(self.parent))]
        labels = []
        buckets = []
        for i in range(len(roots)):
            r = roots[i]
            slot = -1
            for k in range(len(labels)):
                if labels[k] == r:
                    slot = k
                    break
            if slot == -1:
                labels.append(r)
                buckets.append([i])
            else:
                buckets[slot].append(i)
        comps = []
        for members in buckets:
            lo = 0
            for i, c in enumerate(comps):
                if c[0] < members[0]:
                    lo = i + 1
                else:
                    break
            comps.insert(lo, members)
        return comps
