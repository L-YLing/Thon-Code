# Java plugin syntax highlight groups.
# Loaded by plugins/java_support/__init__.py via api.add_syntax_groups()
# so the IDE recognises Java keywords without needing a pre-baked
# assets/languages/java.json (though one can still be provided for richer
# colouring). Groups follow the EditorHighlight convention.

# (group_name, color, is_bold, keywords)
HIGHLIGHT_GROUPS = [
    (
        "java_keywords",
        "#CC7832",
        True,
        [
            "abstract", "assert", "break", "case", "catch", "class", "const",
            "continue", "default", "do", "else", "enum", "extends", "final",
            "finally", "for", "goto", "if", "implements", "import",
            "instanceof", "interface", "native", "new", "package", "private",
            "protected", "public", "return", "static", "strictfp", "super",
            "switch", "synchronized", "this", "throw", "throws", "transient",
            "try", "void", "volatile", "while", "record", "sealed", "non-sealed",
            "permits", "yield", "var",
        ],
    ),
    (
        "java_primitives",
        "#9876AA",
        False,
        [
            "boolean", "byte", "char", "double", "float", "int",
            "long", "short",
        ],
    ),
    (
        "java_literal_null",
        "#6897BB",
        True,
        ["null", "true", "false"],
    ),
    (
        "java_builtin_types",
        "#507874",
        False,
        [
            "String", "Integer", "Long", "Double", "Float", "Boolean",
            "Byte", "Character", "Short", "Object", "System", "Math",
            "Thread", "Runnable", "List", "Map", "Set", "ArrayList",
            "HashMap", "HashSet", "LinkedList", "Optional", "Stream",
            "Arrays", "Collections", "Exception", "RuntimeException",
            "Error", "Throwable", "Enum", "Class",
        ],
    ),
    (
        "java_modifiers",
        "#CC7832",
        False,
        [],
    ),
]

# (language_id_or_extension, groups) tuples as expected by
# PluginAPI.add_syntax_groups(). We register for both "java" id and ".java"
# extension so highlighting kicks in regardless of how the caller opens a
# Java file.
HIGHLIGHT_BINDINGS = [
    ("java", HIGHLIGHT_GROUPS),
    (".java", HIGHLIGHT_GROUPS),
]
