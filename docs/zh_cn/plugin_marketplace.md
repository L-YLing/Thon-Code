# Thon Code 插件市场搭建指南 v1.0

> 面向希望**自建插件分发服务器**的团队与个人。Thon Code 的插件市场协议是**极简 HTTP/JSON**的，可以用任意静态文件托管（Nginx、GitHub Pages、对象存储、内网 WebDAV 只读镜像…）或动态服务（FastAPI / Flask / Express / Spring）实现。

> **关于版本号的说明**：
> - `host_version` 字段针对的是**插件 API 版本**（`HOST_APP_VERSION`），而非 IDE 正式版本号。
> - IDE 的正式版本号存放在 `.main-version` 文件中，内部预发布代号存放在 `.version` 文件中。插件市场和插件清单应使用正式版本号相关的表述。

---

## 目录

1. [协议总览](#1-协议总览)
2. [最小可运行的市场：纯静态文件](#2-最小可运行的市场纯静态文件)
3. [index.json 规范](#3-indexjson-规范)
4. [插件包（ZIP）规范](#4-插件包zip规范)
5. [可选的 SHA-256 校验](#5-可选的-sha-256-校验)
6. [用 GitHub Pages / Gitee Pages 托管](#6-用-github-pages--gitee-pages-托管)
7. [用对象存储（OSS/S3/COS）托管](#7-用对象存储osss3cos托管)
8. [用 FastAPI 搭一个动态市场（带鉴权）](#8-用-fastapi-搭一个动态市场带鉴权)
9. [客户端侧配置](#9-客户端侧配置)
10. [故障排查](#10-故障排查)

---

## 1. 协议总览

Thon Code 客户端（`PluginMarketplace` 类）只向服务端发**两类请求**：

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `GET` | `{market_url}/index.json` | 获取插件索引，返回当前市场中所有可用插件 |
| `GET` | `package_url`（任意绝对 URL） | 下载某个插件包 zip 并安装 |

**没有：认证头、查询参数、分页、搜索、PUT/POST 上传。所有功能靠服务端自行组织 `index.json`来实现。**

这样设计的原因：

- 极简 → 静态托管就能跑；
- 无状态 → 利于 CDN；
- 安全面最小 → 客户端只读，不会向服务器写数据。

---

## 2. 最小可运行的市场：纯静态文件

目录结构：

```
my-market/
├── index.json                      # 插件索引
├── hello_world-1.0.0.zip           # 包 1
├── my_linter-1.2.0.zip             # 包 2
└── my_linter-1.2.1.zip             # 包 1.2.1 的升级版
```

本地临时起一个静态服务器测试：

```bash
cd my-market
python -m http.server 8765
```

然后在 Thon Code → 设置 → 「插件市场 URL」里填入 `http://localhost:8765` → 保存 → 打开插件管理 → 切到「插件市场」标签 → 点击「刷新列表」，就能看到 `index.json` 中列出的插件。

---

## 3. index.json 规范

```json
{
  "version": 1,
  "updated_at": "2025-01-15T10:30:00Z",
  "plugins": [
    {
      "id": "hello_world",
      "name": "Hello World",
      "version": "1.0.0",
      "author": "Demo Author",
      "description": "在状态栏显示问候，演示最小插件。",
      "package_url": "http://localhost:8765/hello_world-1.0.0.zip",
      "package_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "host_version": ">=0.4.0",
      "requires": [
        {"name": "core_utils", "version": ">=1.0.0,<2.0.0"}
      ]
    }
  ]
}
```

### 3.1 顶层字段

| 字段 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| `version` | ✅ | 整数 | 协议版本，目前必须为 `1` |
| `updated_at` | 可选 | ISO-8601 字符串 | 人类可读的最近更新时间，供调试 / 缓存判断 |
| `plugins` | ✅ | 数组 | 插件条目列表 |

### 3.2 `plugins[]` 条目字段

| 字段 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| `id` | ✅ | `str` | 插件唯一 ID，**必须与插件类的 `name` 字段一致**（否则安装后无法识别为同一插件，会重复加载） |
| `name` | ✅ | `str` | UI 展示名 |
| `version` | ✅ | `str` | 语义化版本号；客户端用它判断「更新」 |
| `author` | 可选 | `str` | 作者名 |
| `description` | ✅ | `str` | 列表中展示的简介 |
| `package_url` | ✅ | `str` | 绝对 URL（`http(s)://...`），指向 zip 包 |
| `package_sha256` | 可选 | `str` | zip 文件的 SHA-256 十六进制摘要；提供时客户端会校验 |
| `host_version` | 可选 | `str` | 要求的宿主版本约束，语法同 `requires` |
| `requires` | 可选 | 数组 | 对其它插件的依赖，格式同 `PluginBase.requires` |

> ⚠️ `id` + `version` 是客户端判断「安装 / 更新 / 不重复」的关键字段。如果同一 id 出现多条，客户端以**最后一条**为准（你应避免在 `plugins` 里重复）。

---

## 4. 插件包（ZIP）规范

zip 解压后**必须**是以下两种布局之一，否则客户端会认为包损坏：

### 4.1 单文件插件 zip（直接包含 .py）

```
hello_world-1.0.0.zip
└── hello_world.py        # 根部就是插件文件
```

安装结果：`<plugins_dir>/hello_world.py`。

### 4.2 多文件包插件 zip（包含目录 + __init__.py）

```
my_linter-1.2.0.zip
└── my_linter/
    ├── __init__.py
    ├── checks.py
    └── rules.py
```

安装结果：`<plugins_dir>/my_linter/__init__.py` 等。

### 4.3 打包小抄

```bash
# 单文件
cd build/
zip hello_world-1.0.0.zip hello_world.py

# 多文件（注意：zip 根内必须是目录，不能把 checks.py 直接裸露在根）
cd build/
zip -r my_linter-1.2.0.zip my_linter/
```

解压时客户端会**忽略** zip 内的 `__pycache__/`、`*.pyc`、`.DS_Store` 等垃圾文件，但建议打包前用 `zip -x` 排除。

---

## 5. 可选的 SHA-256 校验

如果 `index.json` 里填了 `package_sha256`，客户端在下载完 zip 后：

```
1. 计算字节流 SHA-256
2. 与 package_sha256.lower() 比较
3. 不一致 → 返回错误状态，不写入 plugins_dir
```

本地生成：

```bash
# Windows PowerShell
Get-FileHash .\hello_world-1.0.0.zip -Algorithm SHA256

# macOS / Linux
sha256sum hello_world-1.0.0.zip
```

> 对内网可信环境可以不填；对公开市场强烈建议加上，否则 CDN 或中间人替换 zip 客户端无法识别。

---

## 6. 用 GitHub Pages / Gitee Pages 托管

### 6.1 仓库布局

```
my-plugin-market/
├── index.json
├── packages/
│   ├── hello_world-1.0.0.zip
│   └── my_linter-1.2.1.zip
└── README.md
```

### 6.2 `index.json` 里的 `package_url`

```json
{
  "version": 1,
  "plugins": [
    {
      "id": "hello_world",
      "name": "Hello World",
      "version": "1.0.0",
      "description": "...",
      "package_url": "https://<user>.github.io/my-plugin-market/packages/hello_world-1.0.0.zip"
    }
  ]
}
```

### 6.3 开启 Pages

- GitHub：仓库 → Settings → Pages → Source 选 `main` 分支根目录；
- Gitee：仓库 → 服务 → Gitee Pages → 同样选根目录。

等 1~2 分钟后用 `https://<user>.github.io/my-plugin-market/` 作为市场 URL 即可。

### 6.4 CDN 与缓存

GitHub Pages 默认有较激进的 Cache-Control。发布新版本时建议：

1. 新包用新文件名（带版本号），不要覆盖旧 zip；
2. 在 `index.json` 更新到新版本 `package_url`；
3. 必要时在仓库根加 `.nojekyll` 空文件，避免 Jekyll 过滤以下划线开头的路径。

---

## 7. 用对象存储（OSS/S3/COS）托管

各大厂商对象存储几乎都支持「静态网站托管」或「公共读 + CDN」，流程完全一致：

1. 创建一个 Bucket；
2. 上传 `index.json` 与所有 zip，并设置 ACL 为「公共读」；
3. 绑定自定义域名（可选，强烈推荐，后续换存储不影响客户端）；
4. 在 Bucket 的「静态网站」页获取根 URL，即为 Thon Code 的插件市场 URL。

如果要做权限控制（例如内部市场仅公司网络可访问），可以在 CDN 层做 IP 白名单或 Referer 防盗链；客户端本身用的是标准 HTTP，不会发任何自定义鉴权头。

---

## 8. 用 FastAPI 搭一个动态市场（带鉴权）

适合需要**登录后才能下载**、**按用户返回不同插件集合**、**统计下载量**的场景。

最小示例：

```python
# market_server.py
from fastapi import FastAPI, HTTPException, Header, Response
from fastapi.staticfiles import StaticFiles
import hashlib
import os

app = FastAPI()

# 简单的 Bearer Token 白名单（生产请用数据库）
VALID_TOKENS = {"tok_xxx_employee_1", "tok_xxx_employee_2"}

PACKAGES_DIR = "packages"  # 目录内存放所有 zip

INDEX = {
    "version": 1,
    "plugins": [
        {
            "id": "internal_linter",
            "name": "团队代码规范检查",
            "version": "2.0.0",
            "author": "Platform Team",
            "description": "仅内部使用的 Python/Rust 混合 Linter。",
            "package_url": "https://market.example.com/packages/internal_linter-2.0.0.zip",
            "requires": [{"name": "core_utils", "version": ">=1.0.0"}],
        },
    ],
}


def _auth(authorization: str | None) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    token = authorization.split(" ", 1)[1]
    if token not in VALID_TOKENS:
        raise HTTPException(status_code=403, detail="Invalid token")


@app.get("/index.json")
def get_index(authorization: str | None = Header(default=None)):
    _auth(authorization)
    return INDEX


@app.get("/packages/{filename}")
def download(filename: str, authorization: str | None = Header(default=None)):
    _auth(authorization)
    path = os.path.join(PACKAGES_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Not found")
    with open(path, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    headers = {"X-SHA256": sha}
    return Response(content=data, media_type="application/zip", headers=headers)
```

启动：

```bash
pip install fastapi uvicorn
uvicorn market_server:app --host 0.0.0.0 --port 8000 --ssl-keyfile privkey.pem --ssl-certfile fullchain.pem
```

客户端配置市场 URL 为 `https://market.example.com`。由于客户端使用的是标准 `urllib.request`，它不会主动附加 Bearer Token；在需要鉴权的部署里，有两种常见做法：

- **方案 A（推荐）**：VPN / 内网 IP 白名单，不做应用层鉴权；
- **方案 B**：下载 URL 改为带签名 query（`?token=...` 或 `?expires=...&sig=...`），在 `package_url` 字段里直接写入带签名的绝对 URL；客户端是「GET 什么 URL 就下什么」，不会改写 query。

---

## 9. 客户端侧配置

### 9.1 设置里填 URL

路径：Thon Code → 菜单栏「文件」→「设置」→「插件市场 URL」。

- 留空（默认）：关闭在线安装，插件市场标签仅提示「未配置」；
- 填 `http(s)://host:port/path`：启用，`GET {URL}/index.json` 拿到索引。

保存后 i18n 文案为 `plugins.market_url_saved`（「市场地址已保存。」）。

### 9.2 在插件管理面板的市场标签操作

流程：

1. 打开插件管理 → 切换到「插件市场」；
2. 如果 URL 改过，点「保存地址」；
3. 点「刷新列表」→ 看到 `plugins.market_fetched`（「已获取 N 个插件包。」）；
4. 选中一个插件 → 点「安装 / 更新」：
   - 下载；
   - （若提供）校验 SHA-256；
   - 解压到 `<plugins_dir>/`；
   - 提示 `plugins.market_installed`，用户回到「已安装」标签点「刷新」即可加载。

---

## 10. 故障排查

| 现象 | 常见原因 | 排查 |
| --- | --- | --- |
| 点「刷新列表」后永远 0 条 | URL 填错 / 服务端没起 / CORS（浏览器控制不存在，urllib 本身不做 CORS，但反代可能拦 User-Agent） | 手动 `curl -I {URL}/index.json` 看 HTTP 状态码；检查响应是不是 JSON 格式，顶层是否有 `plugins` 字段 |
| 能看到列表，但下载后提示「安装失败」 | zip 布局不符合规范（解压后既不是单 py 也不是带 `__init__.py` 的目录） | 本地把 zip 解压到一个空目录，肉眼检查结构 |
| SHA-256 校验失败 | `index.json` 里写的哈希与实际文件不一致；或 CDN 返回了旧文件 | 重新对服务器上的 zip 算哈希；清 CDN 缓存 |
| 装了但「已安装」里没出现 | 插件类没继承 `PluginBase`；或插件 `name` 与市场条目的 `id` 不一致导致被归类错 | 点「刷新」；看 `test/log/` 日志里 `plugin_manager` 的报错 |
| 内网自签 HTTPS 市场连接失败 | `urllib` 默认拒绝自签证书 | 把公司根 CA 装进系统证书存储；或服务端暂时降级为 HTTP（仅可信内网） |

---

## 12. 官方示例插件条目（index.json 范本）

为方便市场运营，Thon Code 官方仓库自带了两个插件，可直接放入你自建的插件市场。推荐把它们打包进 `plugins/` 子目录压缩分发，或在服务器上直接产出以下两份 ZIP：

| ZIP 名 | 对应仓库位置 | 说明 |
| --- | --- | --- |
| `java_support-0.1.0.zip` | `src/thoncode/plugins/java_support/` | 复杂结构包：4 模块 + Python 包 `__init__.py` 组织 |
| `rust_support-0.1.0.zip` | `src/thoncode/plugins/rust_support.py` | 简单结构单文件插件 |

### 12.1 推荐 index.json 条目

```json
{
  "schema_version": 1,
  "plugins": [
    {
      "id": "java_support",
      "name": "Java 支持（高亮+补全+跳转）",
      "version": "0.1.0",
      "minimum_app_version": "0.5.0",
      "author": "Thon Code Official",
      "description": "提供 Java 语言的关键字高亮、java.lang/java.util 常用类补全、以及基于 SymbolLoader 懒加载的跨文件跳转定义，支持 sealed/record 等 JDK 17 新语法。",
      "download_url": "https://your-market.example.com/pkgs/java_support-0.1.0.zip",
      "sha256": "<填充 zip 的 SHA-256>",
      "size_bytes": 0,
      "dependencies": [],
      "tags": ["language", "java", "completion", "navigation"],
      "changelog": "首个稳定版本：高亮 + 补全 230+ 条 + 自定义 Java import 解析"
    },
    {
      "id": "rust_support",
      "name": "Rust 语法高亮",
      "version": "0.1.0",
      "minimum_app_version": "0.5.0",
      "author": "Thon Code Official",
      "description": "为 Rust (`.rs`) 提供关键字 / 类型 / 字面量 / 宏 / 属性等语法高亮；补全与跳转直接复用 SymbolLoader 内置 Rust 抽取器，无需额外开销。",
      "download_url": "https://your-market.example.com/pkgs/rust_support-0.1.0.zip",
      "sha256": "<填充 zip 的 SHA-256>",
      "size_bytes": 0,
      "dependencies": [],
      "tags": ["language", "rust", "highlight"],
      "changelog": "首个稳定版本"
    }
  ]
}
```

> 备注：
> - Java 插件解压后目录名与插件 `name = java_support` 保持一致，ID 与 `PluginBase.name` 匹配；
> - Rust 插件 ZIP 根目录就是单文件 `rust_support.py`，PluginManager 会自动把它归入 `plugins/`。

---

## 13. 标签页 / 补全 / 跳转 与 插件市场的关系

- 标签页（TabManager）、智能补全（EditorCompletion）、Ctrl+右键跳转（EditorNavigation）都是 IDE 核心层能力。它们既可以配合 `plugins/java_support` 这类复杂插件得到更好体验，也可以独立使用核心内置的 fallback 正则抽取器；
- 插件市场是**分发渠道**：把 `java_support` / `rust_support` 打包成 zip 发布即可让所有用户在 IDE 内置的「插件市场」界面一键安装；
- 如果你是团队管理员：可以在 index.json 里只收录 Java 或只收录 Rust 插件，以匹配团队的实际技术栈。

---

**相关文档**：[插件开发指南](./plugin_development.md) 第 13~15 节（新插件示例说明）、[用户使用手册](./user_manual.md) 第 5~8 章（标签页/补全/跳转操作）。

