# Thon Code Plugin Marketplace Setup Guide v1.0

> For teams and individuals who want to **self-host a plugin distribution server**. Thon Code's marketplace protocol is intentionally **minimal HTTP/JSON** — you can serve it from any static host (Nginx, GitHub Pages, object storage, a read-only intranet WebDAV mirror…) or a dynamic backend (FastAPI / Flask / Express / Spring).

---

## Table of Contents

1. [Protocol Overview](#1-protocol-overview)
2. [Minimal Working Marketplace: Pure Static Files](#2-minimal-working-marketplace-pure-static-files)
3. [index.json Schema](#3-indexjson-schema)
4. [Plugin Package (ZIP) Layout](#4-plugin-package-zip-layout)
5. [Optional SHA-256 Verification](#5-optional-sha-256-verification)
6. [Hosting on GitHub Pages / Gitee Pages](#6-hosting-on-github-pages--gitee-pages)
7. [Hosting on Object Storage (OSS / S3 / COS)](#7-hosting-on-object-storage-oss--s3--cos)
8. [A Dynamic Marketplace with FastAPI (and Auth)](#8-a-dynamic-marketplace-with-fastapi-and-auth)
9. [Client-Side Configuration](#9-client-side-configuration)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Protocol Overview

The Thon Code client (the `PluginMarketplace` class) only sends **two kinds of requests** to the server:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `{market_url}/index.json` | Fetch the plugin index — every plugin known to the marketplace |
| `GET` | `package_url` (any absolute URL) | Download a plugin zip and install it |

There is **no** authentication header, query parameter, pagination, search, or `PUT`/`POST` upload. All behaviour above that layer is implemented by the server by organising `index.json`.

Why this design:

- Minimal → a static host is enough;
- Stateless → CDN-friendly;
- Smallest attack surface → the client is read-only and never writes data back.

---

## 2. Minimal Working Marketplace: Pure Static Files

Directory layout:

```
my-market/
├── index.json                      # Plugin index
├── hello_world-1.0.0.zip           # Plugin pkg 1
├── my_linter-1.2.0.zip             # Plugin pkg 2
└── my_linter-1.2.1.zip             # Upgrade for pkg 2
```

Spin up a local static server for testing:

```bash
cd my-market
python -m http.server 8765
```

Now in Thon Code → **File → Settings → Plugin Marketplace URL**, enter `http://localhost:8765`, save, then open **Tools → Plugin Manager**, switch to the **Marketplace** tab, and click **Refresh List**. You should see the plugins listed in `index.json`.

---

## 3. index.json Schema

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
      "description": "Shows a greeting on the status bar. Minimal demo plugin.",
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

### 3.1 Top-Level Fields

| Field | Required | Type | Notes |
| --- | --- | --- | --- |
| `version` | ✅ | integer | Protocol version; must be `1` for now |
| `updated_at` | optional | ISO-8601 string | Human-readable last-updated timestamp, for debugging / cache-coordination |
| `plugins` | ✅ | array | List of plugin entries |

### 3.2 `plugins[]` Entry Fields

| Field | Required | Type | Notes |
| --- | --- | --- | --- |
| `id` | ✅ | `str` | Unique plugin identifier. **Must exactly match the plugin class `name` field** otherwise the installed plugin won't be recognised as the same object and will double-load. |
| `name` | ✅ | `str` | Display name shown in the UI |
| `version` | ✅ | `str` | Semantic version; the client uses this to decide "upgrade vs same" |
| `author` | optional | `str` | Author name |
| `description` | ✅ | `str` | Short description shown in the list |
| `package_url` | ✅ | `str` | Absolute URL (`http(s)://...`) pointing to the zip file |
| `package_sha256` | optional | `str` | Hex SHA-256 digest of the zip bytes; when supplied the client verifies it before installing |
| `host_version` | optional | `str` | Required host version constraint, same syntax as `requires` |
| `requires` | optional | array | Dependencies on other plugins — same format as `PluginBase.requires` |

> ⚠️ The pair `(id, version)` is how the client decides "install / update / skip". If the same `id` appears more than once, the **last entry wins** — try to avoid duplicates inside `plugins`.

---

## 4. Plugin Package (ZIP) Layout

After extraction the zip **must** match one of two layouts, otherwise the client treats it as corrupted.

### 4.1 Single-File Plugin Zip (just a `.py`)

```
hello_world-1.0.0.zip
└── hello_world.py        # Plugin file lives directly at the zip root
```

Installs to: `<plugins_dir>/hello_world.py`.

### 4.2 Multi-File Package Zip (a folder with `__init__.py`)

```
my_linter-1.2.0.zip
└── my_linter/
    ├── __init__.py
    ├── checks.py
    └── rules.py
```

Installs to: `<plugins_dir>/my_linter/__init__.py` + siblings.

### 4.3 Packaging Cheatsheet

```bash
# Single file
cd build/
zip hello_world-1.0.0.zip hello_world.py

# Multi file (the zip root MUST be the folder, not checks.py directly)
cd build/
zip -r my_linter-1.2.0.zip my_linter/
```

The installer automatically ignores junk such as `__pycache__/`, `*.pyc`, and `.DS_Store`, but it's good hygiene to exclude them while zipping with `zip -x`.

---

## 5. Optional SHA-256 Verification

If `index.json` carries `package_sha256`, after downloading the zip the client:

```
1. Compute SHA-256 of the raw bytes
2. Case-insensitive compare against package_sha256
3. On mismatch → returns an error status, never writes to plugins_dir
```

Generate locally:

```powershell
# Windows PowerShell
Get-FileHash .\hello_world-1.0.0.zip -Algorithm SHA256
```

```bash
# macOS / Linux
sha256sum hello_world-1.0.0.zip
```

> For trusted intranet environments you can skip it. For public marketplaces we **strongly** recommend including a digest — otherwise a CDN or MITM can silently swap the zip and the client won't notice.

---

## 6. Hosting on GitHub Pages / Gitee Pages

### 6.1 Repository Layout

```
my-plugin-market/
├── index.json
├── packages/
│   ├── hello_world-1.0.0.zip
│   └── my_linter-1.2.1.zip
└── README.md
```

### 6.2 `package_url` inside `index.json`

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

### 6.3 Turn Pages On

- **GitHub**: Repository → **Settings → Pages** → Source pick `main` branch + `/ (root)`;
- **Gitee**: Repository → **Services → Gitee Pages** → same root option.

Wait 1–2 minutes and the base URL (`https://<user>.github.io/my-plugin-market/`) becomes your Thon Code marketplace URL.

### 6.4 CDN & Caching

GitHub Pages applies fairly aggressive `Cache-Control`. When you publish a new release:

1. Upload the new zip under a **new** versioned filename, don't overwrite an old one;
2. Update `index.json` to point at the new `package_url`;
3. Optionally drop an empty `.nojekyll` file at the repo root so Jekyll doesn't filter paths beginning with `_`.

---

## 7. Hosting on Object Storage (OSS / S3 / COS)

All major object-storage vendors either expose a "Static website hosting" mode or support "public read + CDN", and the procedure is identical:

1. Create a bucket;
2. Upload `index.json` and all zips, set ACL to **public-read**;
3. (Strongly recommended) Bind a custom domain name so later storage migrations don't invalidate client configs;
4. Copy the "Website endpoint" URL — that's the marketplace URL you paste into Thon Code.

If you need access control (e.g. an internal marketplace only reachable from the corporate network), enforce it at the CDN layer via IP whitelists or Referer anti-hotlinking; the client itself uses plain standard HTTP and never injects custom auth headers.

---

## 8. A Dynamic Marketplace with FastAPI (and Auth)

Suitable when you need per-user plugin sets, login-gated downloads, or download-count metrics.

Minimal example:

```python
# market_server.py
from fastapi import FastAPI, HTTPException, Header, Response
import hashlib
import os

app = FastAPI()

# Toy bearer-token allow-list (use a DB in production)
VALID_TOKENS = {"tok_xxx_employee_1", "tok_xxx_employee_2"}

PACKAGES_DIR = "packages"   # All zips live here

INDEX = {
    "version": 1,
    "plugins": [
        {
            "id": "internal_linter",
            "name": "Team Code-Style Linter",
            "version": "2.0.0",
            "author": "Platform Team",
            "description": "Mixed Python/Rust linter for internal use only.",
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

Run it:

```bash
pip install fastapi uvicorn
uvicorn market_server:app --host 0.0.0.0 --port 8000 \
  --ssl-keyfile privkey.pem --ssl-certfile fullchain.pem
```

Client-side, point the marketplace URL at `https://market.example.com`. Since the client uses plain `urllib.request`, it won't auto-attach a bearer token. Two common deployment patterns:

- **Option A (recommended)**：VPN + intranet IP whitelist, no app-layer auth.
- **Option B**：Package URLs carry a signed query string (`?token=...` or `?expires=...&sig=...`) and you write those signed URLs straight into the `package_url` field. The client simply GETs whatever URL it's given — it never rewrites the query.

---

## 9. Client-Side Configuration

### 9.1 Fill URL in Settings

Path: Thon Code → **File → Settings → Plugin Marketplace URL**.

- Empty (default): Online install is disabled. The Marketplace tab simply shows "not configured";
- `http(s)://host:port/path`: Enabled, `GET {URL}/index.json` returns the index.

After saving, the i18n toast `plugins.market_url_saved` appears.

### 9.2 Marketplace Tab Flow in Plugin Manager

1. Open Plugin Manager → switch to **Marketplace**;
2. If you just changed the URL, click **Save URL**;
3. Click **Refresh List** → i18n toast `plugins.market_fetched` ("Fetched N plugin packages.");
4. Select one plugin → click **Install / Update**:
   - download the zip;
   - (if present) verify SHA-256;
   - extract into `<plugins_dir>/`;
   - toast `plugins.market_installed`. The user switches back to **Installed** and clicks **Refresh** to actually load it.

---

## 10. Troubleshooting

| Symptom | Common Causes | How to investigate |
| --- | --- | --- |
| Refresh List always yields 0 entries | Wrong URL; server down; reverse-proxy blocking the UA (urllib doesn't do CORS, but reverse proxies may). | Manually `curl -I {URL}/index.json`, check HTTP status; confirm body is valid JSON and a top-level `plugins` array exists |
| List loads, but install says "Operation failed" | Zip layout doesn't match spec (after extraction there is neither a single `.py` nor a folder containing `__init__.py`) | Extract the zip locally into an empty dir and eyeball it |
| SHA-256 check fails | The hash in `index.json` is stale vs. the actual zip on disk; or CDN returns a cached old zip | Re-hash the server-side zip; purge CDN cache |
| Install succeeded but the plugin doesn't appear in **Installed** | Plugin class doesn't inherit `PluginBase`; or plugin `name` differs from marketplace entry `id` causing classification mismatch | Click **Refresh**; check `test/log/` for `plugin_manager` warnings |
| Intranet self-signed HTTPS marketplace fails to connect | `urllib` rejects self-signed certs by default | Install corporate root CA into system certificate store; or fall back to HTTP inside trusted networks only |

---

**See also**: Sections 10–12 of the [Plugin Development Guide](./plugin_development.md) (packaging & publishing workflow) and Chapter 4 of the [User Manual](./user_manual.md) (plugin-management UI walkthrough).
