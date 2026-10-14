"""
dsa/trie.py -- Unit-V prefix tree.

Used BY the app for the LOCATION SEARCH autocomplete box (/api/search?q=).
"""

class TrieNode:
    """A trie cell with a fixed 40-slot CHILDREN ARRAY (not a dict-tree, so it
    stays honest with 'plain array' storage):
        0-25  -> 'a'..'z'
        26-35 -> '0'..'9'      (Sector 21, Route 7)
        36    -> ' '           (multi-word names)
        37-39 -> apostrophe, '.', '-' (rare in names)
    is_word marks a full key; word holds the pretty original.
    """

    def __init__(self):
        self.children = [None] * 40
        self.is_word = False
        self.word = None

class Trie:
    """Trie over lowercase-normalised location names.

    insert/search/delete O(L) over alphabet 26; autocomplete O(P + k) using the
    is_word/word shortcut when the prefix node keeps its word, else O(P + subtree).
    Space O(26 * nodes) worst case but shared prefixes save the rest.
    """

    def __init__(self):
        self.root = TrieNode()
        self.n_words = 0

    @staticmethod
    def _idx(ch):
        """Map one character to a children-array slot, or -1 if unsupported."""
        if "a" <= ch <= "z":
            return ord(ch) - ord("a")
        if "0" <= ch <= "9":
            return 26 + ord(ch) - ord("0")
        if ch == " ":
            return 36
        if ch == "'":
            return 37
        if ch == ".":
            return 38
        if ch == "-":
            return 39
        return -1

    def _walk(self, key):
        """Return the node for prefix `key` or None. O(L)."""
        node = self.root
        for ch in key:
            i = self._idx(ch)
            if i < 0:
                return None
            node = node.children[i]
            if node is None:
                return None
        return node
