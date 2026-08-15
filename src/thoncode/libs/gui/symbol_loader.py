#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code Symbol Loader",
    "Path": ".main.libs.gui.symbol_loader",
    "Entrance": "main.py"
}

"""Lazy symbol indexer used by auto-completion and go-to-definition.

Scans a single source file once (or when its mtime changes) and builds:
  * ``functions``  - list of (name, signature, line_no, file_path)
  * ``classes``    - list of (name, line_no, file_path)
  * ``variables``  - list of (name, line_no, file_path, scope)
  * ``imports``    - list of (module_or_path, symbol, alias, line_no)

The ``SymbolLoaderRegistry`` singleton acts as the cross-file cache:
  * Each file's index is cached by (abs_path, mtime) so re-opening the same
    file or jumping to an imported module does not cause redundant re-parsing.
  * Plugins can register custom ``ImportResolver`` callables for languages
    whose import syntax is not Python-like (Java, Rust, C/C++...).
  * Plugins can also register custom ``SymbolExtractor`` callables that
    understand a language's AST or do regex-based extraction.

Design notes:
  * We intentionally do NOT depend on full AST-parsing libraries (ast,
    tree-sitter, javalang) by default, so the IDE stays lightweight. A
    plugin that wants deeper understanding can plug itself in as an
    extractor and replace the default regex-based extractor.
  * The lazy-load window is on first access to a foreign module through
    ``get_symbols_for_import(...)``; that call is memoised.
"""

import os
import re
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes (kept as plain tuples/dicts for JSON friendliness)
# ---------------------------------------------------------------------------

Symbol = Dict[str, Any]
"""
Common shape for a symbol entry:
{
    "name": str,
    "kind": "function" | "class" | "variable" | "method" | "field",
    "line": int,
    "file": str,
    "signature": str | None,  # e.g. "def foo(a, b=1)" or "class Foo(Bar)"
    "scope": str | None,       # enclosing class / function / module name
}
"""

ImportEntry = Dict[str, Any]
"""
{
    "module": str,        # raw module/path as written in source
    "symbol": str | None, # specific symbol imported (None = whole module)
    "alias": str | None,  # local alias (None if not aliased)
    "line": int,
}
"""


# ---------------------------------------------------------------------------
# Default (regex-based) extractors for supported languages.
# Each callable receives (file_path: str, source: str, language: str) and
# returns (symbols: List[Symbol], imports: List[ImportEntry]).
# ---------------------------------------------------------------------------

def _python_extractor(path: str, src: str, lang: str
                      ) -> Tuple[List[Symbol], List[ImportEntry]]:
    symbols: List[Symbol] = []
    imports: List[ImportEntry] = []
    lines = src.splitlines()
    class_stack: List[str] = []  # stack of class names for current nesting

    # Regex patterns for Python
    re_import = re.compile(
        r"^\s*import\s+([A-Za-z_][\w\.]*)(?:\s+as\s+([A-Za-z_]\w*))?"
    )
    re_from = re.compile(
        r"^\s*from\s+([A-Za-z_][\w\.]*)\s+import\s+"
        r"([A-Za-z_][\w,*\s]+)(?:\s+as\s+([A-Za-z_]\w*))?"
    )
    re_class = re.compile(r"^(\s*)class\s+([A-Za-z_]\w*)\s*(\([^)]*\))?\s*:")
    re_def = re.compile(r"^(\s*)def\s+([A-Za-z_]\w*)\s*(\([^)]*\))\s*(?:->[^\s:]+)?\s*:")
    re_assign = re.compile(r"^(\s*)([A-Za-z_]\w*)\s*=")

    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")

        # Imports
        m = re_import.match(line)
        if m:
            module, alias = m.group(1), m.group(2)
            imports.append({"module": module, "symbol": None,
                            "alias": alias or module.split(".")[-1], "line": i})
            continue
        m = re_from.match(line)
        if m:
            module, syms, alias = m.group(1), m.group(2), m.group(3)
            for sym in re.split(r"\s*,\s*", syms.strip()):
                if not sym or sym == "*":
                    continue
                local = alias or sym
                imports.append({"module": module, "symbol": sym,
                                "alias": local, "line": i})
            continue

        # Indentation level tracking for classes
        indent_match = re.match(r"^(\s*)", line)
        indent = len(indent_match.group(1).expandtabs(4)) if indent_match else 0
        while class_stack and class_stack[-1][1] >= indent:
            class_stack.pop()

        mc = re_class.match(line)
        if mc:
            indent_level = len(mc.group(1).expandtabs(4))
            cname = mc.group(2)
            sig = f"class {cname}{mc.group(3) or ''}"
            scope = ".".join([cs[0] for cs in class_stack]) or None
            symbols.append({"name": cname, "kind": "class",
                            "line": i, "file": path,
                            "signature": sig, "scope": scope})
            class_stack.append((cname, indent_level))
            continue

        md = re_def.match(line)
        if md:
            indent_level = len(md.group(1).expandtabs(4))
            fname = md.group(2)
            sig = f"def {fname}{md.group(3)}"
            scope_parts = [cs[0] for cs in class_stack]
            if scope_parts:
                scope = ".".join(scope_parts)
                kind = "method" if any(ind < indent_level for _, ind in class_stack) else "function"
            else:
                scope = None
                kind = "function"
            symbols.append({"name": fname, "kind": kind, "line": i,
                            "file": path, "signature": sig, "scope": scope})
            continue

        # Top-level assignment (module-level variables, crude)
        ma = re_assign.match(line)
        if ma:
            indent_level = len(ma.group(1).expandtabs(4))
            if indent_level == 0:
                vname = ma.group(2)
                # Skip dunder
                if not vname.startswith("__"):
                    symbols.append({"name": vname, "kind": "variable",
                                    "line": i, "file": path,
                                    "signature": None, "scope": None})

    return symbols, imports


def _java_extractor(path: str, src: str, lang: str
                    ) -> Tuple[List[Symbol], List[ImportEntry]]:
    symbols: List[Symbol] = []
    imports: List[ImportEntry] = []
    lines = src.splitlines()
    class_name: Optional[str] = None

    re_import = re.compile(r"^\s*import\s+(static\s+)?([\w\.]+)(?:\.(\w+|\*))?\s*;")
    re_package = re.compile(r"^\s*package\s+([\w\.]+)\s*;")
    re_class = re.compile(r"^\s*(?:public|private|protected|static|final|abstract|\s)*"
                          r"(?:class|interface|enum|record)\s+(\w+)\s*(?:<[^>]+>)?\s*(?:extends\s+\w+[^{]*?)?(?:implements\s+[^{]*?)?\{")
    re_method = re.compile(r"^\s*(?:public|private|protected|static|final|abstract|synchronized|\s)*"
                           r"(?:<[^>]+>\s*)?"
                           r"([\w<>\[\],\s?]+?)\s+(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[^{]*)?\{?")
    re_field = re.compile(r"^\s*(?:public|private|protected|static|final|\s)*"
                          r"([\w<>\[\],\s?]+)\s+(\w+)\s*(?:=[^;]+)?;")

    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")

        mi = re_import.match(line)
        if mi:
            module_base = mi.group(2)
            symbol = mi.group(3)
            if symbol and symbol != "*":
                imports.append({"module": module_base, "symbol": symbol,
                                "alias": symbol, "line": i})
            else:
                last = module_base.split(".")[-1]
                imports.append({"module": module_base, "symbol": None,
                                "alias": last, "line": i})
            continue

        mpkg = re_package.match(line)
        if mpkg:
            imports.append({"module": "__package__", "symbol": mpkg.group(1),
                            "alias": None, "line": i})
            continue

        mc = re_class.search(line)
        if mc:
            cname = mc.group(1)
            class_name = cname
            symbols.append({"name": cname, "kind": "class", "line": i,
                            "file": path, "signature": line.strip(),
                            "scope": None})
            continue

        mm = re_method.match(line)
        if mm and class_name:
            rtype, mname, params = mm.group(1), mm.group(2), mm.group(3)
            if mname in ("if", "for", "while", "switch", "return"):
                continue
            sig = f"{rtype.strip()} {mname}({params.strip()})"
            symbols.append({"name": mname, "kind": "method", "line": i,
                            "file": path, "signature": sig,
                            "scope": class_name})
            continue

        mf = re_field.match(line)
        if mf and class_name:
            ftype, fname = mf.group(1), mf.group(2)
            if ftype.strip() in ("return", "throw", "new"):
                continue
            symbols.append({"name": fname, "kind": "field", "line": i,
                            "file": path, "signature": f"{ftype.strip()} {fname}",
                            "scope": class_name})

    return symbols, imports


def _rust_extractor(path: str, src: str, lang: str
                    ) -> Tuple[List[Symbol], List[ImportEntry]]:
    symbols: List[Symbol] = []
    imports: List[ImportEntry] = []
    lines = src.splitlines()
    current_impl: Optional[str] = None

    re_use = re.compile(r"^\s*use\s+([\w:]+)(?:\s+as\s+(\w+))?\s*(?:::\s*\{\s*([^}]+)\s*\})?\s*;")
    re_mod = re.compile(r"^\s*mod\s+(\w+)\s*(?:;|\{)")
    re_struct = re.compile(r"^\s*(?:pub(?:\(crate\))?\s+)?(?:struct|enum|union|trait|type)\s+(\w+)\b")
    re_impl = re.compile(r"^\s*(?:pub\s+)?impl\s+(?:<[^>]+>\s+)?(?:for\s+)?([A-Za-z_]\w*)")
    re_fn = re.compile(r"^\s*(?:pub(?:\(crate\))?\s+)?(?:async\s+)?fn\s+(\w+)\s*(\([^)]*\))")
    re_let = re.compile(r"^\s*(?:pub\s+)?(?:const|static|let(?:\s+mut)?)\s+(\w+)\s*(?::[^=]+)?=")

    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")

        mu = re_use.match(line)
        if mu:
            module = mu.group(1)
            alias = mu.group(2)
            nested = mu.group(3)
            if nested:
                for n in re.split(r"\s*,\s*", nested.strip()):
                    n = n.split(" as ")[0].strip()
                    imports.append({"module": module, "symbol": n,
                                    "alias": alias or n, "line": i})
            else:
                last = module.split("::")[-1]
                imports.append({"module": module, "symbol": None,
                                "alias": alias or last, "line": i})
            continue

        mm = re_mod.match(line)
        if mm:
            imports.append({"module": "__mod__", "symbol": mm.group(1),
                            "alias": mm.group(1), "line": i})
            continue

        ms = re_struct.search(line)
        if ms:
            sname = ms.group(1)
            symbols.append({"name": sname, "kind": "class", "line": i,
                            "file": path, "signature": line.strip(),
                            "scope": None})
            continue

        mi = re_impl.search(line)
        if mi:
            current_impl = mi.group(1)
            continue

        mf = re_fn.match(line)
        if mf:
            fname = mf.group(1)
            sig = f"fn {fname}{mf.group(2)}"
            symbols.append({"name": fname, "kind": "method" if current_impl else "function",
                            "line": i, "file": path, "signature": sig,
                            "scope": current_impl})
            continue

        ml = re_let.match(line)
        if ml:
            lname = ml.group(1)
            symbols.append({"name": lname, "kind": "variable", "line": i,
                            "file": path, "signature": None, "scope": None})

    return symbols, imports


def _fallback_extractor(path: str, src: str, lang: str
                        ) -> Tuple[List[Symbol], List[ImportEntry]]:
    """Very generic extractor: try C-like / JS-like class / function keywords."""
    symbols: List[Symbol] = []
    lines = src.splitlines()
    re_class = re.compile(r"\b(class|interface|struct|enum)\s+(\w+)")
    re_func = re.compile(r"\b(?:function|func|fn|def)\s+(\w+)\s*\(([^)]*)\)")
    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        mc = re_class.search(line)
        if mc:
            symbols.append({"name": mc.group(2), "kind": "class",
                            "line": i, "file": path, "signature": line.strip(),
                            "scope": None})
            continue
        mf = re_func.search(line)
        if mf:
            sig = f"{mf.group(1)} {mf.group(2)}({mf.group(3)})"
            symbols.append({"name": mf.group(2), "kind": "function",
                            "line": i, "file": path, "signature": sig,
                            "scope": None})
    return symbols, []


_DEFAULT_EXTRACTORS: Dict[str, Callable[[str, str, str], Tuple[List[Symbol], List[ImportEntry]]]] = {
    "python": _python_extractor,
    ".py": _python_extractor,
    "java": _java_extractor,
    ".java": _java_extractor,
    "rust": _rust_extractor,
    ".rs": _rust_extractor,
}


# ---------------------------------------------------------------------------
# Import resolvers: given a raw import string + the current file's
# directory + the current language, return the absolute file path so the
# indexer can lazy-load its symbols.
# ---------------------------------------------------------------------------

def _resolve_python_import(imp: ImportEntry, current_file: str, project_root: str) -> Optional[str]:
    module = imp.get("module")
    if not module:
        return None
    parts = module.split(".")
    rel = False
    if parts and not parts[0]:
        rel = True
        parts = parts[1:]
    candidates: List[str] = []
    search_roots: List[str] = []
    if current_file:
        search_roots.append(os.path.dirname(os.path.abspath(current_file)))
    if project_root:
        search_roots.append(os.path.abspath(project_root))
    if rel:
        # relative: walk up n dots from current file's dir
        base = os.path.dirname(os.path.abspath(current_file)) if current_file else ""
        if base:
            candidates.append(os.path.join(base, *parts[:-1], f"{parts[-1]}.py"))
            candidates.append(os.path.join(base, *parts, "__init__.py"))
    for root in search_roots:
        candidates.append(os.path.join(root, *parts[:-1], f"{parts[-1]}.py"))
        candidates.append(os.path.join(root, *parts, "__init__.py"))
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _resolve_java_import(imp: ImportEntry, current_file: str, project_root: str) -> Optional[str]:
    module = imp.get("module")
    if not module or module.startswith("__"):
        return None
    parts = module.split(".")
    if not project_root:
        return None
    project_root = os.path.abspath(project_root)
    for src_sub in ("src/main/java", "src", "."):
        base = os.path.join(project_root, src_sub)
        candidate = os.path.join(base, *parts[:-1], f"{parts[-1]}.java")
        if os.path.isfile(candidate):
            return candidate
    return None


def _resolve_rust_import(imp: ImportEntry, current_file: str, project_root: str) -> Optional[str]:
    module = imp.get("module")
    if not module:
        return None
    parts = module.replace("::", "/").split("/")
    if current_file:
        cur_dir = os.path.dirname(os.path.abspath(current_file))
        # Same folder .rs file
        c1 = os.path.join(cur_dir, f"{parts[-1]}.rs")
        if os.path.isfile(c1):
            return c1
        c2 = os.path.join(cur_dir, *parts[:-1], f"{parts[-1]}.rs")
        if os.path.isfile(c2):
            return c2
    if project_root:
        pr = os.path.abspath(project_root)
        for sub in ("src",):
            c = os.path.join(pr, sub, *parts[:-1], f"{parts[-1]}.rs")
            if os.path.isfile(c):
                return c
    return None


_DEFAULT_RESOLVERS: Dict[str, Callable[[ImportEntry, str, str], Optional[str]]] = {
    "python": _resolve_python_import,
    ".py": _resolve_python_import,
    "java": _resolve_java_import,
    ".java": _resolve_java_import,
    "rust": _resolve_rust_import,
    ".rs": _resolve_rust_import,
}


# ---------------------------------------------------------------------------
# SymbolLoaderRegistry singleton
# ---------------------------------------------------------------------------

class SymbolLoaderRegistry:
    """Cross-file cache of symbols, imports, extractors and import resolvers.

    Thread-safe for lazy background indexing on large projects: the
    per-file indexer only holds ``_lock`` when mutating the ``_cache``
    dict so GUI stays responsive.
    """

    _instance: Optional["SymbolLoaderRegistry"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "SymbolLoaderRegistry":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self) -> None:
        self._cache: Dict[str, Tuple[float, List[Symbol], List[ImportEntry]]] = {}
        self._import_resolvers: Dict[str, Callable[[ImportEntry, str, str], Optional[str]]] = dict(_DEFAULT_RESOLVERS)
        self._extractors: Dict[str, Callable[[str, str, str], Tuple[List[Symbol], List[ImportEntry]]]] = dict(_DEFAULT_EXTRACTORS)
        self._lock = threading.Lock()

    # ----- Extensibility points (used by plugins via PluginAPI wrappers) -----

    def register_extractor(self, language_or_ext: str,
                           extractor: Callable[[str, str, str], Tuple[List[Symbol], List[ImportEntry]]]) -> None:
        """Register a custom symbol extractor for a language / extension.

        Args:
            language_or_ext: Either a language id like "java" or a
                file extension like ".java". Both variants are checked
                so plugins only need to register once.
            extractor: Signature ``(path, source, lang) -> (symbols, imports)``.
        """
        with self._lock:
            self._extractors[language_or_ext] = extractor

    def register_import_resolver(self, language_or_ext: str,
                                 resolver: Callable[[ImportEntry, str, str], Optional[str]]) -> None:
        """Register a custom import resolver for a language / extension."""
        with self._lock:
            self._import_resolvers[language_or_ext] = resolver

    # ----- Indexing -----

    def _lang_key_candidates(self, language: str, file_path: Optional[str]) -> List[str]:
        cands: List[str] = []
        if language:
            cands.append(language)
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            if ext:
                cands.append(ext)
        return cands

    def _pick(self, registry: Dict[str, Any], language: str, file_path: Optional[str], default: Any) -> Any:
        for c in self._lang_key_candidates(language, file_path):
            if c in registry:
                return registry[c]
        return default

    def index_file(self, file_path: str, language: str,
                   force_refresh: bool = False) -> Tuple[List[Symbol], List[ImportEntry]]:
        """Read & index a file. Cached by ``(abs_path, mtime)``.

        Args:
            file_path: Absolute path to the source file. Missing files
                yield empty lists (never raises).
            language: Internal language id, e.g. "python", "java", "rust".
            force_refresh: If True, skip cache and re-parse regardless of mtime.

        Returns:
            (symbols, imports)
        """
        if not file_path:
            return [], []
        abs_path = os.path.abspath(file_path)
        try:
            mtime = os.path.getmtime(abs_path)
        except OSError:
            return [], []

        with self._lock:
            cached = self._cache.get(abs_path)
            if not force_refresh and cached and cached[0] == mtime:
                return cached[1], cached[2]

        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
        except OSError:
            return [], []

        extractor = self._pick(self._extractors, language, abs_path, _fallback_extractor)
        symbols, imports = extractor(abs_path, src, language)

        with self._lock:
            self._cache[abs_path] = (mtime, symbols, imports)
        return symbols, imports

    def index_text(self, text: str, language: str, file_path: Optional[str] = None
                   ) -> Tuple[List[Symbol], List[ImportEntry]]:
        """Index raw text (unsaved editor buffer). Not cached on disk."""
        extractor = self._pick(self._extractors, language, file_path, _fallback_extractor)
        return extractor(file_path or "<memory>", text, language)

    # ----- Imported-symbol lazy loading -----

    def resolve_import(self, imp: ImportEntry, current_file: str,
                       project_root: str, language: str) -> Optional[str]:
        """Resolve an import entry to an absolute file path."""
        resolver = self._pick(self._import_resolvers, language, current_file, lambda *_: None)
        return resolver(imp, current_file, project_root)

    def get_symbols_for_import(self, imp: ImportEntry, current_file: str,
                               project_root: str, language: str
                               ) -> Tuple[Optional[str], List[Symbol]]:
        """Lazily load symbols from the file ``imp`` points at.

        Returns:
            (resolved_path_or_None, symbols)
        """
        resolved = self.resolve_import(imp, current_file, project_root, language)
        if not resolved:
            return None, []
        # Pick the language by extension (rough, but sufficient for indexing)
        ext = os.path.splitext(resolved)[1].lower()
        target_lang = language
        if ext == ".py":
            target_lang = "python"
        elif ext == ".java":
            target_lang = "java"
        elif ext == ".rs":
            target_lang = "rust"
        syms, _ = self.index_file(resolved, target_lang)
        return resolved, syms

    # ----- Aggregation helpers used by completion UI -----

    def collect_local_symbols(self, file_path: str, language: str,
                              live_text: Optional[str] = None
                              ) -> Tuple[List[Symbol], List[ImportEntry]]:
        """Return symbols for the CURRENT file, preferring unsaved editor text."""
        if live_text is not None:
            return self.index_text(live_text, language, file_path)
        return self.index_file(file_path, language)

    def collect_completion_keywords(self, file_path: str, language: str,
                                    project_root: str,
                                    live_text: Optional[str] = None
                                    ) -> List[Tuple[str, Optional[str]]]:
        """Return a flat list of ``(name, signature_or_None)`` for completion.

        Order: local symbols first, then imported symbols (sorted by proximity).
        Deduplicated by name so popups stay small.
        """
        local_syms, imports = self.collect_local_symbols(file_path, language, live_text)
        seen: set = set()
        result: List[Tuple[str, Optional[str]]] = []

        def _push(name: str, sig: Optional[str]) -> None:
            if not name or name in seen:
                return
            seen.add(name)
            result.append((name, sig))

        # 1. Locals
        for s in local_syms:
            _push(s["name"], s.get("signature"))

        # 2. Imports (lazy)
        for imp in imports:
            if imp.get("module") == "__package__" or imp.get("module") == "__mod__":
                continue
            sym = imp.get("symbol")
            alias = imp.get("alias")
            if sym and sym != "*":
                # specific symbol import
                resolved, foreign_syms = self.get_symbols_for_import(
                    imp, file_path, project_root, language)
                matched = [fs for fs in foreign_syms if fs["name"] == sym]
                if matched:
                    _push(alias or sym, matched[0].get("signature"))
                else:
                    _push(alias or sym, None)
            else:
                # whole-module import: alias only
                if alias:
                    _push(alias, f"<module {imp.get('module')}>")
                resolved, foreign_syms = self.get_symbols_for_import(
                    imp, file_path, project_root, language)
                for fs in foreign_syms:
                    # Only top-level items
                    if fs.get("scope"):
                        continue
                    if alias:
                        _push(f"{alias}.{fs['name']}", fs.get("signature"))
                    else:
                        _push(fs["name"], fs.get("signature"))

        return result

    # ----- Go-to-definition helpers -----

    def find_definition(self, identifier: str, file_path: str, language: str,
                        project_root: str, live_text: Optional[str] = None
                        ) -> Optional[Symbol]:
        """Return the symbol entry where ``identifier`` is defined.

        Priority: 1) local exact match, 2) imported exact match (including
        aliases). On success returns a Symbol with file + line.
        """
        if not identifier:
            return None

        local_syms, imports = self.collect_local_symbols(file_path, language, live_text)
        for s in local_syms:
            if s["name"] == identifier:
                return s
            # Class.method form
            if "." in identifier:
                scope, bare = identifier.split(".", 1)
                if s.get("scope") == scope and s["name"] == bare:
                    return s

        # Match against imports
        for imp in imports:
            if imp.get("module") in ("__package__", "__mod__"):
                continue
            alias = imp.get("alias")
            symbol = imp.get("symbol")
            # Case 1: import foo (alias=foo); user typed foo.bar
            if identifier.startswith(f"{alias}.") and not symbol:
                rest = identifier[len(alias) + 1:]
                resolved, foreign = self.get_symbols_for_import(
                    imp, file_path, project_root, language)
                for fs in foreign:
                    if fs["name"] == rest and not fs.get("scope"):
                        return fs
            # Case 2: from foo import bar as alias; user typed alias
            if symbol and (identifier == alias or identifier == symbol):
                resolved, foreign = self.get_symbols_for_import(
                    imp, file_path, project_root, language)
                for fs in foreign:
                    if fs["name"] == symbol:
                        return fs

        return None
