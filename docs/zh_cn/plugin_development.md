# Thon Code 插件开发指南 v1.0

> 适用于 Thon Code >= 0.4.0。本文档介绍如何从零编写、打包并调试一个 Thon Code 插件。

---

## 目录

1. [插件系统概览](#1-插件系统概览)
2. [快速开始：Hello World](#2-快速开始hello-world)
3. [插件元数据与权限声明](#3-插件元数据与权限声明)
4. [生命周期钩子](#4-生命周期钩子)
5. [事件钩子（Hooks）](#5-事件钩子hooks)
6. [PluginAPI 使用参考](#6-pluginapi-使用参考)
7. [菜单注册与快捷键绑定](#7-菜单注册与快捷键绑定)
8. [语法高亮扩展](#8-语法高亮扩展)
9. [插件依赖与版本约束](#9-插件依赖与版本约束)
10. [单文件 vs 多文件包插件](#10-单文件-vs-多文件包插件)
11. [热重载与调试](#11-热重载与调试)
12. [PyInstaller / Nuitka 打包兼容](#12-pyinstaller--nuitka-打包兼容)

---

## 1. 插件系统概览

Thon Code 的插件系统位于 `src/thoncode/libs/plugins/`，由以下核心模块组成：

| 模块 | 职责 |
| --- | --- |
| `plugin_base.py` | 定义 `PluginBase` 基类、权限常量、依赖声明语法 |
| `plugin_api.py`   | 暴露给插件的稳定 API 面（`PluginAPI`），所有操作都走这层 |
| `plugin_manager.py` | 插件加载/卸载/热重载、权限弹窗、依赖排序 |
| `plugin_marketplace.py` | 插件市场客户端（下载、校验、解压安装） |

插件与宿主是**弱耦合**的：插件只能通过 `PluginAPI` 与宿主交互，所有高风险操作在 API 层经过权限校验。

---

## 2. 快速开始：Hello World

### 2.1 最简单文件插件

在 `src/thoncode/plugins/`（或打包后的 `plugins/` 目录）下新建 `hello_world.py`：

```python
#! /usr/bin/env python3
from libs.plugins import PluginBase

class HelloWorldPlugin(PluginBase):
    name        = "hello_world"
    version     = "1.0.0"
    description = "在状态栏显示 Hello World（示例插件）"
    author      = "Your Name"

    def on_load(self):
        self.api.show_status("Hello, Thon Code!")

    def on_unload(self):
        self.api.show_status("Bye!")
```

然后：

1. 启动 Thon Code → 菜单栏「工具」→「插件管理」。
2. 点击「刷新」，应能看到 `hello_world 1.0.0`，状态为「已加载」。
3. 底部状态栏会闪现 `Hello, Thon Code!`。
4. 点击「卸载」→ 状态栏显示 `Bye!`，点击「热重载」→ 重新加载最新文件。

### 2.2 监听文件打开事件

```python
class HelloWorldPlugin(PluginBase):
    # ... 元数据同上 ...

    def on_file_open(self, file_path: str):
        logger = self.api.get_logger(self.name)
        logger.info("用户打开了文件: %s", file_path)
        self.api.show_status(f"已打开: {file_path}")
```

---

## 3. 插件元数据与权限声明

### 3.1 必选元数据

每个插件类必须覆写以下 4 个字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `name` | `str` | 插件唯一 ID，`[a-z0-9_]+`，同名插件会被覆盖 |
| `version` | `str` | [语义化版本](https://semver.org/lang/zh-CN/)，如 `1.2.3` |
| `description` | `str` | 插件管理面板中展示的简介 |
| `author` | `str` | 作者名 / 团队名 |

### 3.2 权限声明（`permissions`）

插件**按需申请**权限；首次加载时宿主会弹出授权对话框，用户可逐条勾选：

```python
from libs.plugins import PluginBase, PERMISSION_MENU_REGISTER, PERMISSION_HOTKEY_BIND

class MyPlugin(PluginBase):
    permissions = [
        PERMISSION_MENU_REGISTER,   # 注册菜单项
        PERMISSION_HOTKEY_BIND,     # 绑定全局快捷键
    ]
```

完整权限列表（定义于 `plugin_base.py`）：

| 常量 | 值 | 说明 |
| --- | --- | --- |
| `PERMISSION_FILESYSTEM_READ`  | `filesystem:read`   | 读取项目外任意文件 |
| `PERMISSION_FILESYSTEM_WRITE` | `filesystem:write`  | 写入项目外任意文件 |
| `PERMISSION_NETWORK`          | `network`           | 发起网络请求（含 HTTP / Socket） |
| `PERMISSION_EXECUTE`          | `execute`           | 启动外部子进程 |
| `PERMISSION_CONFIG`           | `config`            | 读写宿主全局配置 |
| `PERMISSION_EDITOR_MODIFY`    | `editor:modify`     | 修改编辑器内容 / 选区 |
| `PERMISSION_MENU_REGISTER`    | `ui:menu_register`  | 注册菜单项 |
| `PERMISSION_HOTKEY_BIND`      | `ui:hotkey_bind`    | 绑定全局快捷键 |
| `PERMISSION_HIGHLIGHT_EXTEND` | `editor:highlight_extend` | 扩展语法高亮规则 |
| `PERMISSION_PLUGIN_MANAGE`    | `plugins:manage`    | 加载 / 卸载 / 重载其它插件 |

> 低风险 API（如 `get_project_root`、`get_current_theme`、`show_status`、`get_logger`）**不需要**任何权限。

### 3.3 宿主版本要求（`host_version`）

```python
class MyPlugin(PluginBase):
    host_version = ">=0.4.0,<2.0.0"   # 与 requires 语法一致
```

### 3.4 依赖声明（`requires`）

```python
class LintPlugin(PluginBase):
    requires = [
        {"name": "core_utils", "version": ">=1.0.0,<2.0.0"},
        {"name": "sdk_base",   "version": "==3.2.1"},
    ]
```

支持的约束语法：`==`、`>=`、`>`、`<=`、`<`，多个约束用逗号分隔，如 `>=1.0,<2.0`。若依赖缺失或版本不兼容，宿主会跳过加载该插件并在日志中提示（对应 i18n 键 `plugins.dep_missing` / `plugins.dep_version_mismatch`）。

---

## 4. 生命周期钩子

### `on_load()`

插件**首次加载成功并授权完成后**调用。在这里做初始化：注册菜单、绑定快捷键、初始化资源。

```python
def on_load(self):
    self.api.add_menu_item(
        menu_path="tools.my_plugin",
        label="执行我的操作",
        command=self._do_work,
    )
```

### `on_unload()`

插件被**卸载 / 热重载前**调用。必须**幂等**——即使 `on_load` 失败也要能安全调用。典型清理动作：

- 关闭文件句柄、网络连接；
- 持久化插件私有数据（写入 `get_project_root()/.thoncode/` 或 `set_config`）。

> 菜单 / 快捷键 / 语法高亮扩展由 `PluginAPI` **自动清理**，插件无需手动 undo。

---

## 5. 事件钩子（Hooks）

除 `on_load` / `on_unload` 外，插件可以定义任意 `on_<事件名>` 方法，宿主在对应事件广播时调用。

当前支持的事件（也列在 `plugin_api.py` 头部注释）：

| 钩子签名 | 触发时机 |
| --- | --- |
| `on_file_open(path: str)`   | 编辑器打开一个文件时 |
| `on_file_save(path: str)`   | 文件保存成功后 |
| `on_file_close(path: str)`  | 编辑器标签关闭时 |
| `on_editor_change(text: str)` | 编辑器内容变更（节流） |
| `on_tree_refresh()`         | 左侧文件树刷新完成 |
| `on_theme_change(name: str)`| 用户切换主题时 |
| `on_project_open(path: str)`| 用户打开项目文件夹时 |
| `on_syntax_highlight_ext()` | 语法高亮规则重建后 |

示例：

```python
def on_project_open(self, path: str):
    logger = self.api.get_logger(self.name)
    logger.info("新项目根目录: %s", path)
```

---

## 6. PluginAPI 使用参考

`PluginAPI` 是插件访问宿主的**唯一入口**，通过 `self.api` 拿到。

### 6.1 日志

```python
logger = self.api.get_logger(self.name)
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告")
logger.error("错误", exc_info=True)
```

日志输出到标准日志通道，也会被测试框架捕获到 `src/thoncode/test/log/`。

### 6.2 状态栏

```python
self.api.show_status("已处理 123 个文件")
```

### 6.3 项目 / 文件信息

| API | 说明 | 权限 |
| --- | --- | --- |
| `get_project_root() -> str` | 当前项目根目录（绝对路径），未打开则 `""` | 无需 |
| `get_current_file() -> Optional[str]` | 当前编辑器活动标签的文件路径 | 无需 |
| `get_recent_projects() -> List[str]` | 最近打开项目列表 | 无需 |

### 6.4 编辑器只读访问

| API | 说明 | 权限 |
| --- | --- | --- |
| `get_editor_text() -> str` | 获取编辑器全文（`"1.0"` 到末尾） | 无需 |
| `get_editor_selection() -> str` | 获取当前选中文本 | 无需 |

### 6.5 编辑器写入（需 `PERMISSION_EDITOR_MODIFY`）

| API | 说明 |
| --- | --- |
| `set_editor_text(text: str)` | 覆盖编辑器全部内容 |
| `insert_editor_text(text, position="insert")` | 在光标处（或给定 Tk 位置）插入 |

### 6.6 配置（写入需 `PERMISSION_CONFIG`）

| API | 说明 |
| --- | --- |
| `get_config() -> dict` | 读取宿主配置快照（只读，不建议直接改返回值） |
| `set_config(key, value) -> bool` | 写入并持久化一个配置键 |

### 6.7 文件系统（项目外读写需对应权限）

若只需要读写**项目内**文件，直接 `os.path.join(self.api.get_project_root(), "...")` 即可，无需权限。

需要跨目录 / 跨盘访问时才用：

| API | 所需权限 |
| --- | --- |
| `read_file_external(path) -> Optional[str]` | `PERMISSION_FILESYSTEM_READ` |
| `write_file_external(path, content) -> bool` | `PERMISSION_FILESYSTEM_WRITE` |

### 6.8 主题 / 外观

| API | 说明 | 权限 |
| --- | --- | --- |
| `get_current_theme() -> str` | 如 `"darkly"` / `"litera"` | 无需 |
| `get_accent_color() -> Optional[str]` | 当前自定义主题色 `#RRGGBB` | 无需 |

### 6.9 网络与进程（需对应权限）

| API | 所需权限 |
| --- | --- |
| `http_get(url, timeout=10.0) -> Optional[bytes]` | `PERMISSION_NETWORK` |
| `run_process(args, cwd=None, timeout=30) -> (code, stdout, stderr)` | `PERMISSION_EXECUTE` |

### 6.10 插件管理（需 `PERMISSION_PLUGIN_MANAGE`）

| API | 说明 |
| --- | --- |
| `get_plugin_names() -> List[str]` | 列出所有已加载插件名 |
| `reload_plugin(name: str) -> bool` | 触发热重载另一个插件 |

### 6.11 i18n

```python
label = self.api.get_text("plugins.refresh")   # 根据当前界面语言返回
```

若键不存在，原样返回 key 字符串。

---

## 7. 菜单注册与快捷键绑定

### 7.1 注册菜单项（需 `PERMISSION_MENU_REGISTER`）

```python
def on_load(self):
    self.api.add_menu_item(
        menu_path="tools.my_plugin",     # 点分路径，自动创建子菜单
        label="格式化当前文件",
        command=self._format,
        accelerator="Ctrl+Shift+F",      # 仅菜单右侧显示的文字
        separator_before=False,
        separator_after=False,
    )

def _format(self):
    text = self.api.get_editor_text()
    # ... 处理 ...
    self.api.set_editor_text(text)
```

### 7.2 绑定快捷键（需 `PERMISSION_HOTKEY_BIND`）

```python
def on_load(self):
    self.api.bind_hotkey("<Control-Shift-F>", self._on_hotkey, scope="editor")
    self.api.bind_hotkey("<F8>",             self._on_global,  scope="global")

def _on_hotkey(self, event):
    self.api.show_status("你按了 Ctrl+Shift+F")

def _on_global(self, event):
    self.api.show_status("全局快捷键 F8 触发")
```

`scope` 取值：

| 值 | 绑到哪里 |
| --- | --- |
| `"global"` | 根窗口，任何时候都生效 |
| `"editor"` | 编辑器文本控件，仅当编辑器获得焦点时 |
| `"menu"`   | 与 `"global"` 等效（预留） |

> ⚠️ 菜单中显示的 `accelerator` 与 `bind_hotkey` 的 `scope="global"` 是**两件事**：前者只负责文字，后者才真正绑定键盘事件。推荐两者同时使用以让 UI 与实际行为一致。

---

## 8. 语法高亮扩展（需 `PERMISSION_HIGHLIGHT_EXTEND`）

插件可以为已有语言增加高亮组，或为新的文件类型注册规则。

```python
from libs.plugins import PluginBase, PERMISSION_HIGHLIGHT_EXTEND

class RustHighlightPlugin(PluginBase):
    permissions = [PERMISSION_HIGHLIGHT_EXTEND]

    def on_load(self):
        self.api.add_syntax_groups(
            language_patterns=[".rs", "rust"],      # 匹配扩展名或内部语言名
            groups=[
                {
                    "name": "rust.keyword.ext",
                    "color": "#569CD6",
                    "words": ["match", "impl", "trait", "async", "await"],
                },
                {
                    "name": "rust.macro",
                    "color": "#C586C0",
                    "regex": [r"\b\w+!\b"],
                },
            ],
        )
```

`groups` 中每个 dict 的字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `name`  | `str` | 唯一标识，同名会覆盖内置组 |
| `color` | `str` | `#RRGGBB` 十六进制颜色 |
| `words` | `List[str]` | 整词匹配列表（会自动做边界匹配） |
| `regex` | `List[str]` | 原始正则表达式列表（Python `re` 语法） |

---

## 9. 插件依赖与版本约束

### 9.1 排序与循环检测

`PluginManager` 加载时会对所有插件做**拓扑排序**：被依赖者先加载。若出现循环依赖（A→B→A），宿主会：

- 记日志（`plugins.dep_cycle` 文案）；
- 退回「按插件名字母序」加载；
- 加载失败在 UI 中标注状态。

### 9.2 失败不中断整体

单个插件因依赖 / 语法 / 权限缺失而加载失败时，宿主会**跳过它并继续加载剩余插件**，保证 IDE 主体可用。

---

## 10. 单文件 vs 多文件包插件

插件目录中的条目支持两种布局：

### 10.1 单文件（入门推荐）

```
plugins/
└── hello_world.py           # 内含一个 PluginBase 子类
```

加载规则：`import hello_world`，扫描模块中**所有**继承自 `PluginBase` 的类并各实例化一个。你可以在一个 `.py` 里放多个插件类，但推荐一个文件一个。

### 10.2 多文件包（复杂插件）

```
plugins/
└── my_linter/
    ├── __init__.py          # 从子模块 re-export 出插件类
    ├── checks.py            # 业务逻辑模块
    ├── rules.py
    └── README.md            # 打包时的说明文件（不参与 import）
```

`__init__.py` 示例：

```python
# plugins/my_linter/__init__.py
from .checks import LinterPlugin

__all__ = ["LinterPlugin"]
```

> 打包成 zip 发布到插件市场时，解压结果**必须**对应上面任一布局（要么单个 `.py`，要么含 `__init__.py` 的目录）。

---

## 11. 热重载与调试

### 11.1 热重载流程

1. 用户在插件管理面板点击「热重载」（或另一个持有 `PERMISSION_PLUGIN_MANAGE` 的插件调用 `api.reload_plugin(name)`）；
2. `PluginManager` 执行：
   - 调用 `on_unload()`；
   - 让 `PluginAPI._unregister_all_for_plugin` 清理菜单 / 快捷键 / 高亮扩展；
   - 从 `sys.modules` 中移除插件模块；
   - 重新 `importlib.import_module` 并创建新实例；
   - 再次走授权 → `on_load()`。
3. 由此实现「不改代码保存 → 点击重载 → 生效」。

### 11.2 调试建议

- 用 `self.api.get_logger(...)` 打日志，不要直接 `print`，避免污染 stdout；
- 故意抛异常看加载是否被正确隔离、日志是否记录；
- 调试菜单 / 快捷键时反复点击「热重载」验证卸载无残留；
- 权限相关 bug 先确认授权对话框里是否勾选了对应的 flag。

---

## 12. PyInstaller / Nuitka 打包兼容

### 12.1 插件目录解析

打包后宿主会按以下优先级解析插件目录：

1. `sys.frozen == True` → `<exe所在目录>/plugins/`（用户可写，市场默认装到这里）；
2. 否则 → `<thoncode包目录>/plugins/`（源码布局）。

因此**不需要把用户插件打包进二进制**。

### 12.2 内置许可模板 / 资源文件

同理，`assets/license/`、`assets/langs/`、`assets/fonts/` 等资源在打包时：

- PyInstaller：请在 `.spec` 中将 `src/thoncode/assets` 整体作为 `datas` 收入；
- Nuitka：加 `--include-data-dir=src/thoncode/assets=thoncode/assets`。

`license_handle.py` 会自动按「源码 / frozen / _MEIPASS」三种情境回退解析路径，确保模板不会因路径丢失而让 LICENSE 管理器下拉为空。

### 12.3 钩子丰富度兼容性

- 菜单注册：`PluginAPI._install_menu_entry` 内建了 fallback 查找 `host.menubar`、`host._menubar`、`host.root.cget("menu")`，只要主窗口暴露了任一引用即可工作；
- 语法高亮扩展：会遍历 `editor_manager` 中所有 `CodeEditor` 实例批量更新；
- 热重载：基于 `importlib.reload` + 模块重导入，对 PyInstaller 的单文件 / 单目录两种模式都有效。

---

**下一步阅读**：[插件市场搭建指南](./plugin_marketplace.md)、[用户使用手册](./user_manual.md)。
