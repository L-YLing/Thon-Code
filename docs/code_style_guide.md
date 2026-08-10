# Thon Code 代码风格指南

## 1. 项目结构

```
src/thoncode/
├── main.py                    # 应用入口，包含 MainWindow 主类
├── assets/                    # 静态资源
│   ├── langs/                 # 多语言 JSON 文件
│   │   ├── zh_cn.json         # 简体中文
│   │   ├── en_us.json         # 英语（美国）
│   │   └── en_uk.json         # 英语（英国）
│   └── icon.ico
└── libs/
    ├── handles/               # 后端逻辑模块
    │   ├── cfg_handle.py      # 配置文件读写
    │   ├── json_handle.py     # JSON 工具
    │   ├── langs_loader.py    # 多语言加载器
    │   ├── langs_handle.py    # 多语言处理器
    │   ├── font_loader.py     # 字体加载
    │   ├── changelog_handle.py
    │   ├── license_handle.py
    │   ├── git_functions.py
    │   └── struct_handle.py
    └── gui/                   # GUI 页面模块
        ├── theme.py           # 主题管理
        ├── lazy_loader.py     # 懒加载器
        ├── welcome_page.py    # 欢迎页
        ├── settings_win.py    # 设置窗口
        ├── project_cfg.py    # 项目配置
        ├── configure_runtime.py
        ├── run_file.py        # 运行文件
        ├── git_window.py      # Git 集成
        ├── tree_manager.py    # 项目树
        ├── license_ui.py      # 许可证管理
        ├── struct_ui.py       # 目录结构查看
        ├── changelog_ui.py    # 更新日志
        ├── editor_ui.py       # 编辑器 UI 组件
        ├── editor_folding.py  # 代码折叠
        ├── editor_completion.py
        ├── editor_highlight.py
        ├── editor_shortcuts.py
        └── code_editor.py     # 代码编辑器
```

## 2. 文件头部规范

每个 Python 文件必须以以下格式开头：

```python
#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",          # 唯一项目标识符
    "Name": "Thon Code",            # 可读项目名称
    "Path": ".main.libs.gui.theme",  # 模块路径（. 代表根目录）
    "Entrance": "main.py"           # 入口文件
}
```

**规则：**
- `#! /usr/bin/env python3` 必须在文件第一行
- `package` 字典必须在 `import` 语句之前
- `Path` 使用 `.` 表示法，从入口目录开始
- `ID` 必须全局唯一

## 3. 命名规范

### 3.1 变量和函数
- 使用 `snake_case` 命名法
- 变量、函数、方法全部使用小写字母
- 常量使用 `UPPER_CASE`
- 私有成员以 `_` 开头

```python
_CONFIG_PATH: str = "config.json"
current_theme: str = "dark"
_max_retries: int = 3

def apply_theme(theme_name: str) -> None:
    ...
```

### 3.2 类名
- 使用 `PascalCase` 命名法
- 类名应清晰表明其职责

```python
class SettingsWindow(ttkb.Toplevel):
class langs_handle:
class TreeManager:
```

### 3.3 i18n 键名
- 使用点号分隔的层级结构
- 格式：`模块.功能.具体项`
- 全小写，用下划线或点号分隔

```json
{
    "main.menu.settings": "设置",
    "settings.theme": "主题",
    "git.commit_success": "提交成功"
}
```

## 4. 返回值格式

所有后端类/函数必须使用统一的 `return_msg` 格式：

```python
return_msg: dict = {
    "status": "success",    # 状态: success / error / warning
    "data": data,           # 返回数据，任意类型
    "code": 200             # 状态码，int 类型
}
return return_msg
```

**状态码约定：**
| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 404 | 资源未找到 |
| 405 | 操作失败 |
| 500 | 服务器/系统错误 |

## 5. 注释规范

### 5.1 语言要求
- **所有注释和文档字符串必须使用英文**
- 不允许使用中文注释

### 5.2 注释原则
- 只写必要的注释，避免冗余
- 聚焦于"为什么"而非"是什么"
- 代码应尽可能自解释

### 5.3 文档字符串
- 所有公共类和函数必须有 docstring
- 必须包含 Args 和 Returns 说明
- 使用 Google 风格

```python
def apply_theme(theme_name: str) -> None:
    """Apply the specified theme.

    Args:
        theme_name: Theme name in project config ("dark" or "light")
    """
```

### 5.4 类文档字符串
```python
class SettingsWindow(ttkb.Toplevel):
    """Settings configuration window for Thon Code.

    Provides controls for language, theme, auto-reload, tab size,
    and font ligatures settings.
    """
```

## 6. 国际化 (i18n) 规范

### 6.1 语言文件
- 存放于 `assets/langs/` 目录
- 使用 JSON 格式
- 支持的语言：`zh_cn`、`en_us`、`en_uk`

### 6.2 使用方式
```python
import libs.langs_loader as langs_loader

class MyWindow:
    def __init__(self, master):
        self.lang = langs_loader.langs()
    
    def _get_text(self, key: str) -> str:
        """Get localized text by dot-separated key.
        
        Args:
            key: Dot-separated i18n key
            
        Returns:
            Localized string or the key itself if not found
        """
        return getattr(self.lang, key.replace('.', '_'), key)
```

### 6.3 规则
- **所有用户可见文本必须使用 i18n**
- 不允许硬编码中文或英文 UI 文本
- 通过 `_get_text(key)` 方法获取本地化文本
- 键名格式：`模块.功能.具体项`

## 7. 模块化设计

### 7.1 目录结构
- **GUI 层** (`libs/gui/`): 所有窗口和 UI 组件
- **逻辑层** (`libs/handles/`): 数据处理、文件操作等后端逻辑
- **分离原则**: GUI 代码与业务逻辑严格分离

### 7.2 模块规则
- 单一职责：每个模块/类只负责一项功能
- 功能集中：重复使用的功能应提取为独立模块
- 最大限制：每个类不超过 50 个方法，每个文件不超过 800 行

### 7.3 懒加载
- GUI 模块使用 `LazyLoader` 延迟加载
- 减少启动时间和内存占用

```python
from libs.gui.lazy_loader import LazyLoader
SettingsWindow = LazyLoader.get('libs.gui.settings_win', 'SettingsWindow')
```

## 8. 主题规范

### 8.1 支持的主题
- `darkly` (默认深色)
- `flatly` (默认浅色)
- `cyborg`、`superhero`、`vapor`、`solar`
- `dracula`、`vscode_dark` (VSCode 深蓝定制)

### 8.2 主题切换
- 通过设置页面实时切换
- 主题值映射：`dark` → 深色主题，`light` → 浅色主题
- 颜色常量在 `theme.py` 中统一管理

## 9. 代码质量检查清单

- [ ] 文件开头有 `#! /usr/bin/env python3`
- [ ] 文件开头有 `package` 字典声明
- [ ] 每个文件不超过 800 行
- [ ] 每个类不超过 50 个方法
- [ ] 所有注释和 docstring 使用英文
- [ ] 所有用户可见文本使用 i18n
- [ ] 返回值使用 `return_msg` 格式
- [ ] GUI 与逻辑代码分离
- [ ] 变量和函数使用 `snake_case`
- [ ] 类使用 `PascalCase`
- [ ] 常量使用 `UPPER_CASE`
- [ ] 无硬编码的用户可见字符串

## 10. Python 版本要求

- 目标版本：Python 3.13+
- 使用现代 Python 特性（如类型注解、`match` 语句等）
- 使用 `pyright` 进行类型检查