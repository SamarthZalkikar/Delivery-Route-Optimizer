"""
dsa/trees.py -- Unit-II trees: BST, threaded binary tree, AVL, B-tree, B+ tree.

Used BY the app for: storing orders by numeric ID (AVL + B-tree both active;
order lookup answers come from the AVL, the B-tree keeps a second index).

Complexities:
  BST   insert/search/delete O(h) = O(n) worst, O(log n) expected random
  AVL   insert/search/delete O(log n) GUARANTEED via 4 rotations
  B-tree/B+ tree O(log n) IO fan-out (node children m >> 2) => why DBs use them
"""

class BSTNode:
    __slots__ = ("key", "val", "left", "right", "parent")

    def __init__(self, key, val=None, parent=None):
        self.key = key
        self.val = val
        self.left = None
        self.right = None
        self.parent = parent

class BST:
    """Plain BST (no balancing). insert O(h), search O(h), delete O(h),
    traversals O(n). h = height; O(log n) on random input, O(n) when skewed
    (that worst case is exactly WHY Unit-II then adds AVL)."""

    def __init__(self):
        self.root = None
        self.n = 0

    def insert(self, key, val=None):
        """Walk down, attach at first empty child; duplicate keys OVERWRITE."""
        if self.root is None:
            self.root = BSTNode(key, val)
            self.n += 1
            return
        cur = self.root
        while True:
            if key == cur.key:
                cur.val = val
                return
            if key < cur.key:
                if cur.left is None:
                    cur.left = BSTNode(key, val, cur)
                    break
                cur = cur.left
            else:
                if cur.right is None:
                    cur.right = BSTNode(key, val, cur)
                    break
                cur = cur.right
        self.n += 1

    def search(self, key, steps_ret=False):
        cur, steps = self.root, 0
        while cur:
            steps += 1
            if key == cur.key:
                return (cur.val, steps) if steps_ret else cur.val
            cur = cur.left if key < cur.key else cur.right
        return (None, steps) if steps_ret else None

    def _min_node(self, node):
        while node.left:
            node = node.left
        return node

    def _transplant(self, u, v):
        """Swap u's subtree with v's (v may be None) in the parent link."""
        if u is None:
            return
        if u.parent is None:
            self.root = v
        elif u is u.parent.left:
            u.parent.left = v
        else:
            u.parent.right = v
        if v is not None:
            v.parent = u.parent

    def delete(self, key):
        """3 textbook cases: leaf, one child, two children (successor swap). O(h)."""
        node = self.root
        while node and node.key != key:
            node = node.left if key < node.key else node.right
        if node is None:
            return False
        if node.left is None:
            self._transplant(node, node.right)
        elif node.right is None:
            self._transplant(node, node.left)
        else:
            succ = self._min_node(node.right)
            if succ.parent is not node:
                self._transplant(succ, succ.right)
                succ.right = node.right
                succ.right.parent = succ
            self._transplant(node, succ)
            succ.left = node.left
            succ.left.parent = succ
        self.n -= 1
        return True

    def inorder(self):
        out, stack, cur = [], [], self.root
        while stack or cur:
            while cur:
                stack.append(cur)
                cur = cur.left
            node = stack.pop()
            out.append(node.key)
            cur = node.right
        return out

    def preorder(self):
        out, stack = [], [self.root] if self.root else []
        while stack:
            node = stack.pop()
            out.append(node.key)
            if node.right:
                stack.append(node.right)
            if node.left:
                stack.append(node.left)
        return out

    def postorder(self):
        """Reverse-adapted preorder (root-right-left) then flip: yields
        left-right-root order without recursion."""
        out, stack = [], [self.root] if self.root else []
        while stack:
            node = stack.pop()
            out.append(node.key)
            if node.left:
                stack.append(node.left)
            if node.right:
                stack.append(node.right)
        out.reverse()
        return out

    def height(self):
        return _h(self.root)

    def items(self):

        stack, cur, out = [], self.root, []
        while stack or cur:
            while cur:
                stack.append(cur)
                cur = cur.left
            node = stack.pop()
            out.append((node.key, node.val))
            cur = node.right
        return out
