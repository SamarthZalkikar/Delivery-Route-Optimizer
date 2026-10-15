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

def _h(node):
    if node is None:
        return 0
    l, r = _h(node.left), _h(node.right)
    return 1 + (l if l > r else r)

class ThreadedNode:
    __slots__ = ("key", "val", "left", "right", "lthread", "rthread")

    def __init__(self, key, val=None):
        self.key = key
        self.val = val
        self.left = self.right = None
        self.lthread = self.rthread = True

class ThreadedBST:
    """Right-threaded binary search tree. Right NULL pointers are replaced by
    threads to the inorder SUCCESSOR, giving O(n) inorder traversal with O(1)
    space -- no stack, no recursion, no parent pointer.
    insert O(h); inorder_threaded O(n) but O(1) extra space."""

    def __init__(self):
        self.root = None
        self.n = 0

    def insert(self, key, val=None):
        """BST insert on a right-threaded tree.
        LEFT child: new node threads RIGHT to its successor (the old parent).
        RIGHT child: new node INHERITS the parent's old successor thread.
        insert O(h)."""
        if self.root is None:
            self.root = ThreadedNode(key, val)
            self.n += 1
            return
        node = self.root
        while True:
            if key == node.key:
                node.val = val
                return
            if key < node.key:
                if not node.lthread:
                    node = node.left
                else:
                    new = ThreadedNode(key, val)
                    new.rthread = True
                    new.right = node
                    new.lthread = True
                    node.lthread = False
                    node.left = new
                    self.n += 1
                    return
            else:
                if not node.rthread:
                    node = node.right
                else:
                    new = ThreadedNode(key, val)
                    new.rthread = node.rthread
                    new.right = node.right
                    new.lthread = True
                    node.rthread = False
                    node.right = new
                    self.n += 1
                    return

    def leftmost(self, node):
        while node.lthread is False and node.left is not None:
            node = node.left
        return node

    def inorder_threaded(self):
        """FOLLOW-THE-thread traversal: zero stack, zero recursion. O(n)."""
        out = []
        cur = self.leftmost(self.root) if self.root else None
        while cur is not None:
            out.append(cur.key)
            if cur.rthread:
                cur = cur.right
            else:
                cur = self.leftmost(cur.right)
        return out

    def __len__(self):
        return self.n

class AVLNode:
    __slots__ = ("key", "val", "left", "right", "h")

    def __init__(self, key, val=None):
        self.key = key
        self.val = val
        self.left = None
        self.right = None
        self.h = 1

    def bf(self):
        l = self.left.h if self.left else 0
        r = self.right.h if self.right else 0
        return l - r

class AVLTree:
    """Self-BALANCING BST: every insert/delete repairs height with the four
    classic rotations, so all O(h) ops become O(log n) guaranteed.
    Rotations implemented: LL (clockwise), RR (counter), LR & RL (double)."""

    def __init__(self):
        self.root = None
        self.n = 0
        self.rotations = 0

    def search(self, key, steps_ret=False):
        cur, steps = self.root, 0
        while cur:
            steps += 1
            if key == cur.key:
                return (cur.val, steps) if steps_ret else cur.val
            cur = cur.left if key < cur.key else cur.right
        return (None, steps) if steps_ret else None

    def contains(self, key):
        """Existence check INDEPENDENT of stored value (delete uses it so a
        found key whose val happens to be None is not confused with a miss)."""
        cur = self.root
        while cur:
            if key == cur.key:
                return True
            cur = cur.left if key < cur.key else cur.right
        return False

    def insert(self, key, val=None):
        self.root = _avl_insert(self.root, key, val, self)
        self.n += 1

    def delete(self, key):
        if not self.contains(key):
            return False
        self.root = _avl_delete(self.root, key, self)
        self.n -= 1
        return True

    def height(self):
        return self.root.h if self.root else 0

    def items(self):
        """In-order key/val walk (iterative, own stack), sorted by key."""
        stack, cur, out = [], self.root, []
        while stack or cur:
            while cur:
                stack.append(cur)
                cur = cur.left
            node = stack.pop()
            out.append((node.key, node.val))
            cur = node.right
        return out

    def rot_right(self, y):
        """LL case fix: clockwise rotation around y. O(1)."""
        x = y.left
        t2 = x.right
        x.right = y
        y.left = t2
        _upd(y)
        _upd(x)
        self.rotations += 1
        return x

    def rot_left(self, x):
        """RR case fix: counter-clockwise rotation around x. O(1)."""
        y = x.right
        t2 = y.left
        y.left = x
        x.right = t2
        _upd(x)
        _upd(y)
        self.rotations += 1
        return y

def _upd(n):
    l = n.left.h if n.left else 0
    r = n.right.h if n.right else 0
    n.h = 1 + (l if l > r else r)

def _avl_insert(node, key, val, tree):
    if node is None:
        return AVLNode(key, val)
    if key < node.key:
        node.left = _avl_insert(node.left, key, val, tree)
    elif key > node.key:
        node.right = _avl_insert(node.right, key, val, tree)
    else:
        node.val = val; tree.n -= 1
        return node
    _upd(node)
    return _rebalance(node, tree)

def _rebalance(node, tree):
    b = node.bf()
    if b > 1:
        if node.left.bf() >= 0:
            return tree.rot_right(node)
        node.left = tree.rot_left(node.left)
        return tree.rot_right(node)
    if b < -1:
        if node.right.bf() <= 0:
            return tree.rot_left(node)
        node.right = tree.rot_right(node.right)
        return tree.rot_left(node)
    return node

def _avl_delete(node, key, tree):
    if node is None:
        return None
    if key < node.key:
        node.left = _avl_delete(node.left, key, tree)
    elif key > node.key:
        node.right = _avl_delete(node.right, key, tree)
    else:
        if node.left is None:
            return node.right
        if node.right is None:
            return node.left
        succ = node.right
        while succ.left:
            succ = succ.left
        node.key, node.val = succ.key, succ.val
        node.right = _avl_delete(node.right, succ.key, tree)
    _upd(node)
    return _rebalance(node, tree)

class BTreeNode:
    __slots__ = ("keys", "vals", "children", "leaf")

    def __init__(self, leaf):
        self.keys = []
        self.vals = []
        self.children = []
        self.leaf = leaf

class BTree:
    """B-tree of minimum degree t (== CLRS B-TREE). Insert with preemptive
    splits, search O(t log_t n), DELETE with all borrow/merge cases.
    WHY databases love it: one node covers a big DISK BLOCK, so fan-out t>=64
    means tiny height (a million rows is 3-4 levels) => few random reads."""
