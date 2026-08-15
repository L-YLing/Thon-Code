# Thon Code Documentation Index

> Naming convention: `[module]-[type]-[version].md`
> Last updated: 2026-08-14

## Document Catalog

### Developer Guides

| Module | Type | Version | English (en_us) | Chinese (zh_cn) | Status |
|--------|------|---------|-----------------|-----------------|--------|
| code_editor | dev_guide | v1.0 | [en_us/code_editor-dev_guide-v1.0.md](en_us/code_editor-dev_guide-v1.0.md) | [zh_cn/code_editor-dev_guide-v1.0.md](zh_cn/code_editor-dev_guide-v1.0.md) | Active |
| file_tree | dev_guide | v1.0 | [en_us/file_tree-dev_guide-v1.0.md](en_us/file_tree-dev_guide-v1.0.md) | [zh_cn/file_tree-dev_guide-v1.0.md](zh_cn/file_tree-dev_guide-v1.0.md) | Active |
| async_utils | dev_guide | v1.0 | [en_us/async_utils-dev_guide-v1.0.md](en_us/async_utils-dev_guide-v1.0.md) | [zh_cn/async_utils-dev_guide-v1.0.md](zh_cn/async_utils-dev_guide-v1.0.md) | Active |
| code_style | style_guide | v1.0 | — | [zh_cn/code_style_guide.md](zh_cn/code_style_guide.md) | Chinese only |

### Plugin Development

| Document | English (en_us) | Chinese (zh_cn) | Status |
|----------|-----------------|-----------------|--------|
| Plugin Development Guide | [en_us/plugin_development.md](en_us/plugin_development.md) | [zh_cn/plugin_development.md](zh_cn/plugin_development.md) | Active |
| Plugin Marketplace Guide | [en_us/plugin_marketplace.md](en_us/plugin_marketplace.md) | [zh_cn/plugin_marketplace.md](zh_cn/plugin_marketplace.md) | Active |

### User Manual

| Document | English (en_us) | Chinese (zh_cn) | Status |
|----------|-----------------|-----------------|--------|
| User Manual | [en_us/user_manual.md](en_us/user_manual.md) | [zh_cn/user_manual.md](zh_cn/user_manual.md) | Active |

## Directory Structure

```
docs/
├── INDEX.md                          # This file
├── code_style_guide.md               # Code style guide (Chinese)
├── en_us/                            # English documents
│   ├── README/
│   │   └── README.md
│   ├── code_editor-dev_guide-v1.0.md
│   ├── file_tree-dev_guide-v1.0.md
│   ├── async_utils-dev_guide-v1.0.md
│   ├── plugin_development.md
│   ├── plugin_marketplace.md
│   └── user_manual.md
└── zh_cn/                            # Chinese documents
    ├── plugin/
    ├── code_style_guide.md
    ├── code_editor-dev_guide-v1.0.md
    ├── file_tree-dev_guide-v1.0.md
    ├── async_utils-dev_guide-v1.0.md
    ├── plugin_development.md
    ├── plugin_marketplace.md
    └── user_manual.md
```

## Version Note

Thon Code uses two version files:

- **`.main-version`**: The public-facing version number for end users and plugin developers. This is the version you should reference in documentation, plugin manifests, and user-facing communications.
- **`.version`**: Internal build/preview version code used for pre-release builds and internal tracking. Do not reference this in public documentation.

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
| 2026-08-14 | Cleanup | Removed legacy unsplit bilingual docs, old TODO/code_status, obsolete plugin define.md, outdated en_us CHANGELOG |
| 2026-08-14 | Added | Plugin development, plugin marketplace, and user manual docs to index |
| 2026-08-14 | Added | Version note clarifying .main-version vs .version usage |
