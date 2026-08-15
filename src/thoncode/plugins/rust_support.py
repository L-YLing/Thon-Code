#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-plugin-rust-support",
    "Name": "Rust Syntax Support (Simple Plugin)",
    "Path": ".main.plugins.rust_support",
    "Entrance": "main.py"
}

"""Single-file example plugin that adds Rust syntax highlighting.

Demonstrates the simplest "one file = one plugin" pattern using
``PERMISSION_HIGHLIGHT_EXTEND``. Unlike the Java plugin which ships
custom extractors and completion symbols, the Rust plugin only provides
keyword groups so the built-in Rust extractor in SymbolLoader can still
power go-to-definition.
"""

from libs.plugins import PluginBase, PERMISSION_HIGHLIGHT_EXTEND


# (group_name, color, bold, keywords)
_RUST_GROUPS = [
    (
        "rust_keywords",
        "#CC7832",
        True,
        [
            "as", "async", "await", "break", "const", "continue", "crate",
            "dyn", "else", "enum", "extern", "false", "fn", "for", "if",
            "impl", "in", "let", "loop", "match", "mod", "move", "mut",
            "pub", "ref", "return", "self", "Self", "static", "struct",
            "super", "trait", "true", "type", "unsafe", "use", "where",
            "while", "abstract", "become", "box", "do", "final", "macro",
            "override", "priv", "typeof", "unsized", "virtual", "yield",
            "try",
        ],
    ),
    (
        "rust_builtin_types",
        "#9876AA",
        False,
        [
            "bool", "char", "f32", "f64", "i8", "i16", "i32", "i64",
            "i128", "isize", "str", "u8", "u16", "u32", "u64", "u128",
            "usize",
            "String", "Vec", "Option", "Result", "Box", "Rc", "Arc",
            "Cell", "RefCell", "Mutex", "RwLock", "HashSet", "HashMap",
            "BTreeSet", "BTreeMap", "Cow", "PhantomData", "Pin",
            "Default", "Clone", "Copy", "Drop", "Eq", "PartialEq", "Ord",
            "PartialOrd", "Debug", "Display", "Into", "From", "Iterator",
            "IntoIterator", "Extend", "AsRef", "AsMut", "Deref", "DerefMut",
            "Fn", "FnMut", "FnOnce", "Read", "Write", "Seek", "BufRead",
            "ToOwned", "ToString", "Send", "Sync", "Sized", "Unpin",
            "Any", "Error",
            "Ok", "Err", "Some", "None",
            "println", "print", "eprintln", "eprint", "format", "dbg",
            "vec", "assert", "assert_eq", "assert_ne", "todo", "unimplemented",
            "panic",
        ],
    ),
    (
        "rust_macros",
        "#BBB529",
        False,
        [],  # populated implicitly by highlight regex; list is extensible
    ),
    (
        "rust_literals",
        "#6897BB",
        True,
        ["true", "false"],
    ),
]

# register both for language-id "rust" and extension ".rs"
_HIGHLIGHT_BINDINGS = [
    ("rust", _RUST_GROUPS),
    (".rs", _RUST_GROUPS),
]


class RustSupportPlugin(PluginBase):
    """Simple single-file Rust highlighting plugin."""

    name = "rust_support"
    version = "1.0.0"
    description = "Rust syntax highlighting via keyword groups"
    author = "Thon Code"
    permissions = [
        PERMISSION_HIGHLIGHT_EXTEND,
    ]
    dependencies = []

    def on_load(self) -> None:
        logger = self.api.get_logger(self.name)
        logger.info("Rust support plugin v%s loading...", self.version)
        for lang_or_ext, groups in _HIGHLIGHT_BINDINGS:
            ok = self.api.add_syntax_groups(lang_or_ext, groups)
            logger.debug("add_syntax_groups(%s) -> %s", lang_or_ext, ok)
        logger.info("Rust support plugin loaded.")

    def on_unload(self) -> None:
        logger = self.api.get_logger(self.name)
        logger.info("Rust support plugin unloaded.")


PluginClass = RustSupportPlugin
