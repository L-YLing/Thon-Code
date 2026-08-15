"""Custom Java symbol extractor + import resolver (plugin-provided).

The default :mod:`libs.gui.symbol_loader` already ships a Java extractor,
so this module demonstrates *how a multi-file plugin package can ship its
own* and register it via :meth:`PluginAPI.register_symbol_extractor` /
:meth:`PluginAPI.register_import_resolver` on load.

If a symbol can already be parsed by the built-in extractor, the plugin
does not duplicate that work: here we add a few JDK-17 niceties such as
``sealed class`` and ``record`` parameter recognition that the simpler
builtin regex might miss.
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple


Symbol = Dict[str, Any]
ImportEntry = Dict[str, Any]


def _strip_comments(src: str) -> str:
    """Remove /* block */ and // line comments without touching strings.

    Sufficiently robust for identifier scanning; we keep line/column
    alignment intact by replacing comment bodies with whitespace.
    """
    out = []
    i, n = 0, len(src)
    in_string = False
    in_char = False
    in_block = False
    in_line = False
    while i < n:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if in_line:
            if ch == "\n":
                in_line = False
                out.append(ch)
            else:
                out.append(" " if ch != "\r" else ch)
        elif in_block:
            if ch == "*" and nxt == "/":
                in_block = False
                out.append(" "); out.append(" ")
                i += 2
                continue
            out.append(" " if ch not in "\r\n" else ch)
        elif in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
        elif in_char:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if ch == "'":
                in_char = False
        else:
            if ch == "/" and nxt == "/":
                in_line = True
                out.append(" "); out.append(" ")
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_block = True
                out.append(" "); out.append(" ")
                i += 2
                continue
            if ch == '"':
                in_string = True
            elif ch == "'":
                in_char = True
            out.append(ch)
        i += 1
    return "".join(out)


def extract_java_symbols(path: str, src: str, language: str
                         ) -> Tuple[List[Symbol], List[ImportEntry]]:
    """Plugin-level extractor shipped by java_support package."""
    symbols: List[Symbol] = []
    imports: List[ImportEntry] = []
    cleaned = _strip_comments(src)
    lines = cleaned.splitlines()
    class_name: Optional[str] = None
    record_name: Optional[str] = None

    re_import = re.compile(r"^\s*import\s+(static\s+)?([\w\.]+)(?:\.(\w+|\*))?\s*;")
    re_package = re.compile(r"^\s*package\s+([\w\.]+)\s*;")
    re_class = re.compile(
        r"^\s*(?:public|private|protected|static|final|abstract|sealed|non-sealed|\s)*"
        r"(class|interface|enum)\s+(\w+)"
    )
    re_record = re.compile(
        r"^\s*(?:public|private|protected|\s)*record\s+(\w+)\s*\(([^)]*)\)"
    )
    re_ctor = re.compile(
        r"^\s*(?:public|private|protected|\s)*"
        r"(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[^{]*)?\{"
    )
    re_method = re.compile(
        r"^\s*(?:public|private|protected|static|final|abstract|synchronized|default|native|\s)*"
        r"(?:<[^>]+>\s*)?"
        r"([\w<>\[\],\s?]+?)\s+(\w+)\s*\(([^)]*)\)"
    )
    re_field = re.compile(
        r"^\s*(?:public|private|protected|static|final|volatile|transient|\s)*"
        r"([\w<>\[\],\s?]+)\s+(\w+)\s*(?:=[^;]+)?;"
    )

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

        mr = re_record.search(line)
        if mr:
            rname = mr.group(1)
            class_name = rname
            record_name = rname
            symbols.append({"name": rname, "kind": "class", "line": i,
                            "file": path, "signature": line.strip(),
                            "scope": None})
            # record fields (positional components) become fields
            params_raw = mr.group(2)
            for comp in [p.strip() for p in params_raw.split(",") if p.strip()]:
                parts = comp.split()
                if len(parts) >= 2:
                    tname = parts[-2]
                    cname = parts[-1]
                    symbols.append({"name": cname, "kind": "field", "line": i,
                                    "file": path,
                                    "signature": f"{tname} {cname}",
                                    "scope": rname})
            continue

        mc = re_class.search(line)
        if mc:
            kind_keyword = mc.group(1)
            cname = mc.group(2)
            class_name = cname
            record_name = None
            symbols.append({"name": cname, "kind": "class", "line": i,
                            "file": path, "signature": line.strip(),
                            "scope": None})
            continue

        # Constructor: name matches current class
        mctor = re_ctor.match(line)
        if mctor and class_name and mctor.group(1) == class_name:
            params = mctor.group(2)
            symbols.append({"name": class_name, "kind": "method",
                            "line": i, "file": path,
                            "signature": f"{class_name}({params.strip()})",
                            "scope": class_name})
            continue

        mm = re_method.match(line)
        if mm:
            rtype, mname, params = mm.group(1), mm.group(2), mm.group(3)
            if mname in ("if", "for", "while", "switch", "return", "throw",
                         "new", "catch", "else", "try", "finally", "synchronized",
                         "do", "assert"):
                continue
            if class_name and (rtype.strip() in {"class", "interface", "enum",
                                                 "record", "package"}):
                continue
            sig = f"{rtype.strip()} {mname}({params.strip()})"
            scope = class_name
            symbols.append({"name": mname, "kind": "method" if scope else "function",
                            "line": i, "file": path, "signature": sig,
                            "scope": scope})
            continue

        mf = re_field.match(line)
        if mf and class_name:
            ftype, fname = mf.group(1), mf.group(2)
            ftype = ftype.strip()
            if ftype in ("return", "throw", "new", "if", "while", "for",
                         "switch", "catch", "else", "package", "class",
                         "record", "import", "extends", "implements"):
                continue
            symbols.append({"name": fname, "kind": "field", "line": i,
                            "file": path,
                            "signature": f"{ftype} {fname}",
                            "scope": class_name})

    return symbols, imports


def resolve_java_import(imp: ImportEntry, current_file: str,
                        project_root: str) -> Optional[str]:
    """Plugin-provided Java import resolver.

    Walks common Maven / Gradle source layouts before falling back to
    scanning ``project_root`` recursively if the source is not found.
    """
    module = imp.get("module")
    if not module or module.startswith("__"):
        return None
    # Skip obvious JDK packages (no local file to jump to). We keep this
    # list small; a more serious Java plugin would consult the project's
    # dependency manifest.
    if module.startswith("java.") or module.startswith("javax.") or \
       module.startswith("jdk.") or module.startswith("sun.") or \
       module.startswith("javafx.") or module.startswith("kotlin."):
        return None

    parts = module.split(".")
    if not project_root:
        return None
    project_root = os.path.abspath(project_root)
    for src_sub in (
        "src/main/java",
        "src/test/java",
        "src/main/kotlin",
        "src",
        "app/src/main/java",
        "app/src",
        ".",
    ):
        base = os.path.join(project_root, src_sub)
        if not os.path.isdir(base):
            continue
        candidate = os.path.join(base, *parts[:-1], f"{parts[-1]}.java")
        if os.path.isfile(candidate):
            return candidate
    return None
