#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test - editor_highlight",
    "Path": ".main.test.test_editor_highlight",
    "Entrance": "main.py"
}

import unittest

import _bootstrap  # noqa: F401
from _bootstrap import get_logger

logger = get_logger("test_editor_highlight")


# ---------------------------------------------------------------------------
# Lightweight fakes avoiding Tkinter initialization
# ---------------------------------------------------------------------------
class FakeTextWidget:
    """Records tag operations for assertion without a real tk.Text."""

    def __init__(self, content=""):
        self._content = content
        self.added_tags = []
        self.configured_tags = []
        self.removed_tags = []
        self.deleted_tags = []

    def tag_add(self, tag, start, end=None):
        self.added_tags.append((tag, start, end))

    def tag_config(self, tag, **kwargs):
        self.configured_tags.append(tag)

    def tag_remove(self, tag, start, end=None):
        self.removed_tags.append((tag, start, end))

    def tag_names(self):
        return []

    def tag_delete(self, tag):
        self.deleted_tags.append(tag)

    def get(self, start=None, end=None):
        if start is None:
            return self._content
        # For bracket matching: return the window content.
        return self._content

    def index(self, idx):
        return idx

    def yview(self):
        return (0.0, 1.0)


def make_highlight(parent_groups=None):
    """Create an EditorHighlight bypassing __init__ (no StyleSystem/Tk needed)."""
    from libs.gui.editor_highlight import EditorHighlight
    h = EditorHighlight.__new__(EditorHighlight)
    h.parent = type("P", (), {"groups": parent_groups or [], "_textbox": FakeTextWidget()})()
    h.bracket_pairs = {'(': ')', '[': ']', '{': '}'}
    h._word_index = {}
    h._index_signature = None
    h._tags_configured = False
    h._highlight_after_id = None
    h._ml_state_cache = (None, 0, False)
    h._managed_tags = ("comment", "string", "number", "function", "classname")
    return h


class EditorHighlightTests(unittest.TestCase):
    """Test cases for EditorHighlight performance optimizations."""

    # ------------------------------------------------------------------
    # Constants / structure
    # ------------------------------------------------------------------
    def test_performance_constants_exist(self):
        """Verify performance tuning constants are defined."""
        from libs.gui.editor_highlight import EditorHighlight
        self.assertTrue(hasattr(EditorHighlight, 'LARGE_FILE_THRESHOLD'))
        self.assertTrue(hasattr(EditorHighlight, 'VIEWPORT_BUFFER'))
        self.assertTrue(hasattr(EditorHighlight, 'HIGHLIGHT_DEBOUNCE_MS'))
        self.assertTrue(hasattr(EditorHighlight, 'BRACKET_SCAN_RADIUS'))
        self.assertGreater(EditorHighlight.LARGE_FILE_THRESHOLD, 0)
        self.assertGreater(EditorHighlight.VIEWPORT_BUFFER, 0)
        logger.info("performance_constants_exist: constants verified")
        print("[PASS] test_performance_constants_exist: constants verified")

    def test_package_declaration(self):
        """Verify editor_highlight has proper package declaration."""
        import libs.gui.editor_highlight as mod
        self.assertTrue(hasattr(mod, 'package'))
        self.assertEqual(mod.package['ID'], 'thon-code-gui')
        logger.info("package_declaration: package dict verified")
        print("[PASS] test_package_declaration: package dict verified")

    # ------------------------------------------------------------------
    # Word index
    # ------------------------------------------------------------------
    def test_build_word_index_maps_words_to_tags(self):
        """Verify word index maps each word to its kw_<name> tag."""
        groups = [
            {"name": "keyword", "color": "#C678DD", "words": ["def", "class", "if"]},
            {"name": "builtin", "color": "#61AFEF", "words": ["print", "len"]},
        ]
        h = make_highlight(groups)
        h._build_word_index()
        self.assertEqual(h._word_index["def"], "kw_keyword")
        self.assertEqual(h._word_index["print"], "kw_builtin")
        self.assertEqual(h._index_signature, h._groups_signature())
        logger.info("build_word_index: words mapped to tags correctly")
        print("[PASS] test_build_word_index: words mapped to tags correctly")

    def test_word_index_first_group_wins_on_duplicate(self):
        """Verify first group wins when a word appears in multiple groups."""
        groups = [
            {"name": "keyword", "color": "#C678DD", "words": ["str"]},
            {"name": "type", "color": "#98C379", "words": ["str"]},
        ]
        h = make_highlight(groups)
        h._build_word_index()
        self.assertEqual(h._word_index["str"], "kw_keyword")
        logger.info("word_index_first_group_wins: first group precedence preserved")
        print("[PASS] test_word_index_first_group_wins: first group precedence preserved")

    def test_ensure_word_index_rebuilds_on_groups_change(self):
        """Verify index rebuilds when groups signature changes."""
        h = make_highlight([{"name": "kw", "color": "#000", "words": ["a"]}])
        h._build_word_index()
        self.assertIn("a", h._word_index)
        # Change groups.
        h.parent.groups = [{"name": "kw2", "color": "#000", "words": ["b"]}]
        h._ensure_word_index()
        self.assertNotIn("a", h._word_index)
        self.assertIn("b", h._word_index)
        self.assertEqual(h._word_index["b"], "kw_kw2")
        logger.info("ensure_word_index_rebuilds: index invalidated on groups change")
        print("[PASS] test_ensure_word_index_rebuilds: index invalidated on groups change")

    def test_groups_signature_changes_with_content(self):
        """Verify signature differs when group colors or word counts change."""
        groups_a = [{"name": "kw", "color": "#000", "words": ["a"]}]
        groups_b = [{"name": "kw", "color": "#000", "words": ["a", "b"]}]
        h = make_highlight(groups_a)
        sig_a = h._groups_signature()
        h.parent.groups = groups_b
        sig_b = h._groups_signature()
        self.assertNotEqual(sig_a, sig_b)
        logger.info("groups_signature_changes: signature reflects word count")
        print("[PASS] test_groups_signature_changes: signature reflects word count")

    # ------------------------------------------------------------------
    # Multiline state scanning
    # ------------------------------------------------------------------
    def test_scan_line_multiline_normal_line(self):
        """A normal code line does not enter multiline state."""
        from libs.gui.editor_highlight import EditorHighlight
        self.assertFalse(EditorHighlight._scan_line_multiline("x = 1", False))
        logger.info("scan_line_multiline_normal: normal line stays False")
        print("[PASS] test_scan_line_multiline_normal: normal line stays False")

    def test_scan_line_multiline_unclosed(self):
        """An opening triple quote without close enters multiline state."""
        from libs.gui.editor_highlight import EditorHighlight
        self.assertTrue(EditorHighlight._scan_line_multiline('"""unclosed', False))
        logger.info("scan_line_multiline_unclosed: unclosed triple quote enters multiline")
        print("[PASS] test_scan_line_multiline_unclosed: unclosed triple quote enters multiline")

    def test_scan_line_multiline_closed_same_line(self):
        """A closed triple quote on the same line does not enter multiline."""
        from libs.gui.editor_highlight import EditorHighlight
        self.assertFalse(EditorHighlight._scan_line_multiline('"""closed"""', False))
        logger.info("scan_line_multiline_closed_same_line: closed triple quote stays False")
        print("[PASS] test_scan_line_multiline_closed_same_line: closed triple quote stays False")

    def test_scan_line_multiline_continuation(self):
        """A line inside an open multiline comment stays in multiline."""
        from libs.gui.editor_highlight import EditorHighlight
        self.assertTrue(EditorHighlight._scan_line_multiline("still inside", True))
        logger.info("scan_line_multiline_continuation: inside multiline stays True")
        print("[PASS] test_scan_line_multiline_continuation: inside multiline stays True")

    def test_scan_line_multiline_terminates(self):
        """A closing triple quote exits multiline state."""
        from libs.gui.editor_highlight import EditorHighlight
        self.assertFalse(EditorHighlight._scan_line_multiline('end"""', True))
        logger.info("scan_line_multiline_terminates: closing triple quote exits multiline")
        print("[PASS] test_scan_line_multiline_terminates: closing triple quote exits multiline")

    def test_scan_line_multiline_ignores_triple_quote_in_string(self):
        """A triple quote inside a single-quoted string is not a comment."""
        from libs.gui.editor_highlight import EditorHighlight
        # 'a"""b' opens a single-quoted string; the """ should be ignored.
        self.assertFalse(EditorHighlight._scan_line_multiline("'a\"\"\"b'", False))
        logger.info("scan_line_multiline_ignores_in_string: triple quote in string ignored")
        print("[PASS] test_scan_line_multiline_ignores_in_string: triple quote in string ignored")

    # ------------------------------------------------------------------
    # Line highlighting with word index (O(1) lookup)
    # ------------------------------------------------------------------
    def test_highlight_line_uses_word_index(self):
        """Verify keyword lookup uses the word index (O(1) dict)."""
        groups = [{"name": "keyword", "color": "#C678DD", "words": ["def", "return"]}]
        h = make_highlight(groups)
        h._build_word_index()
        tw = FakeTextWidget()
        h._highlight_line(tw, 1, "def foo():\n", False)
        # The keyword 'def' should be tagged with kw_keyword.
        kw_tags = [t for t in tw.added_tags if t[0] == "kw_keyword"]
        self.assertTrue(any(t[1] == "1.0" for t in kw_tags))
        logger.info("highlight_line_uses_word_index: keyword tagged via dict lookup")
        print("[PASS] test_highlight_line_uses_word_index: keyword tagged via dict lookup")

    def test_highlight_line_string_tag(self):
        """Verify string literals get the string tag."""
        h = make_highlight([])
        h._word_index = {}
        tw = FakeTextWidget()
        h._highlight_line(tw, 1, 'x = "hello"\n', False)
        str_tags = [t for t in tw.added_tags if t[0] == "string"]
        self.assertTrue(len(str_tags) >= 1)
        logger.info("highlight_line_string_tag: string literal tagged")
        print("[PASS] test_highlight_line_string_tag: string literal tagged")

    def test_highlight_line_number_tag(self):
        """Verify numeric literals get the number tag."""
        h = make_highlight([])
        h._word_index = {}
        tw = FakeTextWidget()
        h._highlight_line(tw, 1, "x = 42\n", False)
        num_tags = [t for t in tw.added_tags if t[0] == "number"]
        self.assertTrue(len(num_tags) >= 1)
        logger.info("highlight_line_number_tag: number literal tagged")
        print("[PASS] test_highlight_line_number_tag: number literal tagged")

    def test_highlight_line_function_call_tag(self):
        """Verify an identifier followed by '(' gets the function tag."""
        h = make_highlight([])
        h._word_index = {}
        tw = FakeTextWidget()
        h._highlight_line(tw, 1, "foo()\n", False)
        fn_tags = [t for t in tw.added_tags if t[0] == "function"]
        self.assertTrue(len(fn_tags) >= 1)
        logger.info("highlight_line_function_call_tag: function call tagged")
        print("[PASS] test_highlight_line_function_call_tag: function call tagged")

    def test_highlight_line_classname_tag(self):
        """Verify an identifier after 'class' gets the classname tag."""
        h = make_highlight([])
        h._word_index = {}
        tw = FakeTextWidget()
        h._highlight_line(tw, 1, "class Foo:\n", False)
        # 'class' is not in word_index so it won't be kw-tagged, but Foo after
        # 'class' should be tagged classname.
        cn_tags = [t for t in tw.added_tags if t[0] == "classname"]
        self.assertTrue(len(cn_tags) >= 1)
        logger.info("highlight_line_classname_tag: classname tagged")
        print("[PASS] test_highlight_line_classname_tag: classname tagged")

    # ------------------------------------------------------------------
    # Bracket matching (local scan)
    # ------------------------------------------------------------------
    def test_find_matching_bracket_forward(self):
        """Verify forward bracket matching finds the closing bracket."""
        h = make_highlight([])
        # Window text starting at the cursor's opening bracket.
        tw = FakeTextWidget("(a(b))")
        result = h.find_matching_bracket(tw, "1.0", '(', ')')
        self.assertIsNotNone(result)
        # Match is at offset 5 (the last ')').
        self.assertEqual(result, "1.0+5c")
        logger.info("find_matching_bracket_forward: closing bracket found at offset 5")
        print("[PASS] test_find_matching_bracket_forward: closing bracket found at offset 5")

    def test_find_matching_bracket_unclosed(self):
        """Verify unclosed bracket returns None."""
        h = make_highlight([])
        tw = FakeTextWidget("(unclosed")
        result = h.find_matching_bracket(tw, "1.0", '(', ')')
        self.assertIsNone(result)
        logger.info("find_matching_bracket_unclosed: unclosed bracket returns None")
        print("[PASS] test_find_matching_bracket_unclosed: unclosed bracket returns None")

    def test_find_matching_bracket_no_bracket(self):
        """Verify a non-bracket character returns None."""
        h = make_highlight([])
        tw = FakeTextWidget("abc")
        result = h.find_matching_bracket(tw, "1.0", '(', ')')
        self.assertIsNone(result)
        logger.info("find_matching_bracket_no_bracket: non-bracket returns None")
        print("[PASS] test_find_matching_bracket_no_bracket: non-bracket returns None")

    def test_find_matching_bracket_nested(self):
        """Verify nested brackets match the correct closing bracket."""
        h = make_highlight([])
        tw = FakeTextWidget("(a(b)c)")
        # Cursor at first '(' (offset 0); match should be the final ')' at offset 6.
        result = h.find_matching_bracket(tw, "1.0", '(', ')')
        self.assertEqual(result, "1.0+6c")
        logger.info("find_matching_bracket_nested: nested brackets matched correctly")
        print("[PASS] test_find_matching_bracket_nested: nested brackets matched correctly")

    # ------------------------------------------------------------------
    # Tag config caching
    # ------------------------------------------------------------------
    def test_tag_config_cached(self):
        """Verify tag_config is applied only once until invalidated."""
        groups = [{"name": "keyword", "color": "#C678DD", "words": ["def"]}]
        h = make_highlight(groups)
        h._style_system = type("S", (), {"get_value": lambda self, *a, **kw: "#000"})()
        tw = FakeTextWidget()
        h._ensure_tag_configs(tw)
        first_count = len(tw.configured_tags)
        h._ensure_tag_configs(tw)
        self.assertEqual(len(tw.configured_tags), first_count)
        # Invalidating should allow reconfiguration.
        h._tags_configured = False
        h._ensure_tag_configs(tw)
        self.assertGreater(len(tw.configured_tags), first_count)
        logger.info("tag_config_cached: tag_config applied once per invalidation")
        print("[PASS] test_tag_config_cached: tag_config applied once per invalidation")


if __name__ == "__main__":
    unittest.main(verbosity=2)
