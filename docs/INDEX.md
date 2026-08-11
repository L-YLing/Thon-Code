# Thon Code Documentation Index

> Naming convention: `[module]-[type]-[version].md`
> Last updated: 2026-08-11

## Document Catalog

| Module | Type | Version | English (en_us) | Chinese (zh_cn) | Status |
|--------|------|---------|-----------------|-----------------|--------|
| code_editor | dev_guide | v1.0 | [en_us/code_editor-dev_guide-v1.0.md](en_us/code_editor-dev_guide-v1.0.md) | [zh_cn/code_editor-dev_guide-v1.0.md](zh_cn/code_editor-dev_guide-v1.0.md) | Active |
| file_tree | dev_guide | v1.0 | [en_us/file_tree-dev_guide-v1.0.md](en_us/file_tree-dev_guide-v1.0.md) | [zh_cn/file_tree-dev_guide-v1.0.md](zh_cn/file_tree-dev_guide-v1.0.md) | Active |
| async_utils | dev_guide | v1.0 | [en_us/async_utils-dev_guide-v1.0.md](en_us/async_utils-dev_guide-v1.0.md) | [zh_cn/async_utils-dev_guide-v1.0.md](zh_cn/async_utils-dev_guide-v1.0.md) | Active |
| code_style | style_guide | v1.0 | — | [zh_cn/code_style_guide.md](code_style_guide.md) | Chinese only |

## Legacy Documents (Bilingual, Unsplit)

| File | Description | Action |
|------|-------------|--------|
| [code_editor_dev_guide.md](code_editor_dev_guide.md) | Original bilingual code editor guide | Superseded by split versions |
| [file_tree_dev_guide.md](file_tree_dev_guide.md) | Original bilingual file tree guide | Superseded by split versions |

## Directory Structure

```
docs/
├── INDEX.md                          # This file
├── code_editor_dev_guide.md          # Legacy bilingual (original)
├── code_style_guide.md               # Code style guide (Chinese)
├── file_tree_dev_guide.md            # Legacy bilingual (original)
├── en_us/                            # English documents
│   ├── CHANGELOG.md
│   ├── README/
│   │   └── README.md
│   ├── code_editor-dev_guide-v1.0.md
│   ├── file_tree-dev_guide-v1.0.md
│   └── async_utils-dev_guide-v1.0.md
└── zh_cn/                            # Chinese documents
    ├── TODO.md
    ├── plugin/
    │   └── define.md
    ├── code_status.md
    ├── code_editor-dev_guide-v1.0.md
    ├── file_tree-dev_guide-v1.0.md
    └── async_utils-dev_guide-v1.0.md
```

## Naming Convention

```
[module]-[type]-[version].md
```

- **module**: Feature module name (e.g., `code_editor`, `file_tree`, `async_utils`)
- **type**: Document type (e.g., `dev_guide`, `user_guide`, `style_guide`, `api_ref`)
- **version**: Semantic version (e.g., `v1.0`, `v1.1`, `v2.0`)

### Examples
- `code_editor-dev_guide-v1.0.md` — Code editor developer guide, version 1.0
- `async_utils-dev_guide-v1.0.md` — Async utils developer guide, version 1.0
- `file_tree-api_ref-v1.2.md` — File tree API reference, version 1.2

## Update Log

| Date | Action | Details |
|------|--------|---------|
| 2026-08-11 | Created | Initial index created with 3 module docs (bilingual) |
| 2026-08-11 | Added | async_utils-dev_guide-v1.0 for both en_us and zh_cn |
| 2026-08-11 | Renamed | Applied naming convention to existing docs |
