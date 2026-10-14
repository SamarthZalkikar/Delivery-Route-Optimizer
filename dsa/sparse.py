"""
dsa/sparse.py -- Unit-I sparse matrix as LINKED ROWS.

Used BY the app for the road-distance matrix: the matrix in memory is plain
arrays, but the UI storage view is the linked-row form, showing DENSITY
(nonzero / (rows * cols)).
"""

from dsa.linked import SLNode


class SparseCell:
    __slots__ = ("col", "val", "nxt")

    def __init__(self, col, val, nxt=None):
        self.col = col
        self.val = val
        self.nxt = nxt


class SparseRow:
    """One matrix row: header node + sorted-by-col chain of SparseCell."""
    __slots__ = ("row", "head")

    def __init__(self, row):
        self.row = row
        self.head = None

    def set(self, col, val):
        """Insert/replace keeping ascending column order. O(row nnz)."""
        if self.head is None or col < self.head.col:
            self.head = SparseCell(col, val, self.head)
            return
        prev, cur = None, self.head
        while cur is not None and cur.col < col:
            prev, cur = cur, cur.nxt
        if cur is not None and cur.col == col:
            cur.val = val
        else:
            prev.nxt = SparseCell(col, val, cur)


class SparseMatrix:
    """Sparse matrix as a plain array of SparseRow Headers.

    from_dense copies only nonzero entries. set/get O(row nnz).
    density() = nonzero / (rows*cols) -- the UI shows e.g. '28%'. Memory
    lesson: if density << 0.5 the linked form wins; a full 2-D array wastes
    n^2 cells storing mostly zeros."""

    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.data = [SparseRow(i) for i in range(rows)]
        self.nnz = 0

    @classmethod
    def from_dense(cls, matrix, skip=0.0):
        """Build from a nested array; values <= skip are treated as zero/absent."""
        m = cls(len(matrix), len(matrix[0]) if matrix else 0)
        for i in range(m.rows):
            for j in range(m.cols):
                v = matrix[i][j]
                if v != skip and v is not None:
                    m.data[i].set(j, v)
                    m.nnz += 1
        return m

    def get(self, i, j, default=None):
        """Scan row i for column j. O(row nnz)."""
        cur = self.data[i].head if 0 <= i < self.rows else None
        while cur:
            if cur.col == j:
                return cur.val
            cur = cur.nxt
        return default

    def density(self):
        if self.rows == 0 or self.cols == 0:
            return 0.0
        return self.nnz / (self.rows * self.cols)

    def as_rows_json(self):
        """/api-ready row view: [[row, [[col, val], ...]], ...]."""
        out = []
        for row in self.data:
            cells, cur = [], row.head
            while cur:
                cells.append([cur.col, round(cur.val, 2)])
                cur = cur.nxt
            out.append([row.row, cells])
        return out
