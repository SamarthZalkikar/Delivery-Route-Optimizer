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

    def insert(self, word):
        """Insert a key; ALSO add standalone word-tokens so prefix 'sta' finds
        'Central Station'. insert O(L) per call."""
        key = word.lower()
        node = self.root
        for ch in key:
            i = self._idx(ch)
            if node.children[i] is None:
                node.children[i] = TrieNode()
            node = node.children[i]
        node.word = word
        if not node.is_word:
            node.is_word = True
            self.n_words += 1

    def search(self, word):
        node = self._walk(word.lower())
        return node is not None and node.is_word

    def startswith(self, prefix):
        return self._walk(prefix.lower()) is not None

    def delete(self, word):
        """Bottom-up prune: remove nodes made empty; keep shared prefixes. O(L)."""
        key = word.lower()
        path = []
        node = self.root
        for ch in key:
            i = self._idx(ch)
            node = node.children[i]
            if node is None:
                return False
            path.append((i, node))
        if not node.is_word:
            return False
        node.is_word = False
        node.word = None
        self.n_words -= 1

        parent = self.root
        for i in range(len(path) - 1, -1, -1):
            idx_, dead = path[i]
            if dead.is_word or any(dead.children):
                return True
            parent = self.root if i == 0 else path[i - 1][1]
            parent.children[idx_] = None
        return True

    def __len__(self):
        return self.n_words

    def autocomplete(self, prefix, limit=8):
        """Words starting with prefix: walk to prefix node O(P), then collect
        up to `limit` matches by depth-first walk O(P + k) on the sub-trie."""
        node = self._walk(prefix.lower())
        if node is None:
            return []
        out, stack = [], [(node, prefix.lower())]
        while stack and len(out) < limit:
            cur, key = stack.pop()
            if cur.is_word:
                out.append(cur.word)
            for i in range(39, -1, -1):
                if cur.children[i] is not None:
                    stack.append((cur.children[i], key + self._char(i)))
        return out

    @staticmethod
    def _char(i):
        if i <= 25:
            return chr(ord("a") + i)
        if i <= 35:
            return chr(ord("0") + i - 26)
        return (" ", "'", ".", "-")[i - 36]
