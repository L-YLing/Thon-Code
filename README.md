# 语言 | Languages
**中文(简体)** | [**English**](docs/en_us/README/README.md)

# 长期维护声明
**该项目计划将维护至`2028/7/1`，期间由于作者本人学业压力（作者多为初高中生），将在暑期等有长假期间更新大量内容，期外则将进行零散化更新。如仓库此声明仍存在则表示该项目不会断更。**

# 简介
**这是一个为开源而生的IDE，由Python驱动，并且足够轻量。经过测试，打开一些中小型项目，ThonCode的启动速度与VSCode不差多少(约慢于`VSCode` 0.413s，[点击查看测试信息](#测试))。我们也在积极寻找解决运行时资源占用高、性能弱、启动速度慢等问题。**

# 图标引用许可&原作者署名

文件夹 蓝色的图标 by Papirus Development Team on <a href="https://icon-icons.com/zh/authors/550-papirus-development-team">Icon-Icons.com</a>

文件图标 by Elegantthemes on <a href="https://icon-icons.com/zh/authors/103-elegantthemes">Icon-Icons.com</a> (CC BY 4.0)

蟒蛇图标 by Zayronxio on <a href="https://icon-icons.com/zh/authors/601-zayronxio">Icon-Icons.com</a> (Apache 2.0)

# 核心功能
* [x] **Python代码原生高亮支持**
* [x] **Python代码原生自动补全支持**
* [x] **配置项目依赖、解释器**
* [ ] **内置Shell**
* [ ] **DEBUG调试**
* [ ] **搜索**

# 原生图形化 Git集成 && 开源常用功能集成
* **LICENSE.md 开源协议管理**
* **CHANGELOG.md 版本更新日志管理**
* **`TODO` CODE_STYLE_GUIDE.md 代码规范管理**
* **Git基础操作**
    - **Init: 初始化Git仓库**
    - **Add: 添加文件到暂存区**
    - **Commit: 提交到本地仓库**
    - **Push: 推送到远程仓库**
    - **Pull: 从远程仓库拉取代码**
    - **`TODE` Merge: 合并分支**
* **Github工作流**
    - * **`TODO` 拖动式(图形化)编写工作流文件**
    - * **`TODO` 配置工作流文件**

# 优势
* [x] **i18n支持，我们已经实现了十分便捷的i18n方法，您仅需要提供JSON文件即可（我们参考MC Java模组的设计开发的）**
* [x] **跨平台：我们支持Windows/Linux/macOS(尽管我们并没有发布macOS可运行版本，但是有人试过是可以打包为macOS的安装包安装使用的，另外Linux实际上应该指所有实现了POSIX的类UNIX系统，我们在后续计划支持OpenXJ380OS)**
* [ ] **Git深度集成**
* [ ] **性能优势（尽管我们的启动速度稍慢，但是开项目的速度几乎秒开且与项目规模无关；资源占用低，我们的资源暂用[内存/CPU]总是显著低于VSCode/IDEA[1]）**

# 运行
**您可以选择使用打包好的可执行文件运行或者安装程序安装以使用，它们可以在项目的`release`里找到。如果您想直接运行python程序也可以，但是您需要满足以下条件：**

* **`Windows 10+` / `Linux glibc 2.17+`**
* **`Python 3.13+`**

**按照如下顺序执行命令可以启动`main.py`主程序：**
1. `pip install -r requirements.txt`
2. `python main.py`(Linux上可能需要执行：`python3 main.py`，请进入到main.py所在文件夹执行或修改路径)

# 打包为可执行文件
**现支持打包为可执行文件/安装包的系统平台：**
* **`Windows 10 22H2 +`**
* **`Debian`系Linux发行版(采用`.deb`包格式的发行版)**

**在项目[`tools/`](/tools/README.md)目录下我们提供了`pyinstaller`及`nuitka`的打包脚本，您可以通过文件名来确认使用哪一个。（如`pyinstaller_build_win.bat`用于在Windows系统下使用pyinstaller进行打包）；注意，您需要手动将脚本文件移动到主程序文件（入口程序，一般是`main.py`）同级目录下执行，否则它将会使用错误的路径（当然您也可以手动修改，但不推荐）**

# 使用截图
<img width="1202" height="707" alt="image" src="https://github.com/user-attachments/assets/0499ca67-9980-4554-a87e-90a2ed649cd0" />

<img width="1202" height="707" alt="image" src="https://github.com/user-attachments/assets/fcf90c90-98fa-4a46-a2ec-97f34719ef63" />

# 测试

**以下为基础测试条件：**
| **IDE软件** | **CPU** | **操作系统平台** | **内存** |
| --- | --- | --- | --- |
| **ThonCode** | **Intel G4400** | **Windows** | **DDR4 4GB** |
| **VSCode** | **Intel G4400** | **Windows** | **DDR4 4GB** |

**测试内容：**
| **测试用项目** | **VSCode启动用时** | **ThonCode启动用时** |
| --- | --- | --- |
| **[markitdown](https://github.com/microsoft/markitdown)** | **1.24s** | **1.65s** |
> **内容已过时：在最新版本中，基于懒加载的优化，大型项目Thon Code已可以做到秒开(因为仅仅加载了第一层目录结构，仅在用户展开文件夹时才继续加载下一层内容，当然大文件仍然无法秒开，以及搜索功能目前因为懒加载的原因导致无法正常使用，但是我们已经有了优化思路预计0.0.13版本将会上线)**

# 贡献者
**暂时不想写 OvO**

# 骄傲的感言
**从2023年的`HydronIDE`干到现在的`ThonCode`,我已经可以完全用`ThonCode`来开发`ThonCode`啦！**

---

^[1]: **数据为内部测试，可能不准**