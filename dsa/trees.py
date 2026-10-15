"""
dsa/trees.py -- Unit-II trees: BST, threaded binary tree, AVL, B-tree, B+ tree.

Used BY the app for: storing orders by numeric ID (AVL + B-tree both active;
order lookup answers come from the AVL, the B-tree keeps a second index).

Complexities:
  BST   insert/search/delete O(h) = O(n) worst, O(log n) expected random
  AVL   insert/search/delete O(log n) GUARANTEED via 4 rotations
  B-tree/B+ tree O(log n) IO fan-out (node children m >> 2) => why DBs use them
"""
