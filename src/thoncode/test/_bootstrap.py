#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-test",
    "Name": "Thon Code Test Bootstrap",
    "Path": ".main.test._bootstrap",
    "Entrance": "main.py"
}

import os
import sys
import logging

# 当前文件所在目录 (src/thoncode/test/) 与项目包根目录 (src/thoncode/)
_THIS_DIR: str = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT: str = os.path.dirname(_THIS_DIR)

# 将项目包根目录加入 sys.path，使 libs.* 可被正常导入
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 后端模块使用相对资源路径 (如 assets/config.json)，需将工作目录切换到包根目录
os.chdir(_PROJECT_ROOT)

# 测试日志目录
LOG_DIR: str = os.path.join(_THIS_DIR, "log")
os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """获取配置好的 logger，日志写入 test/log/<name>.log 并输出到控制台

    Args:
        name: 日志名称，通常为测试模块名
    Returns:
        logging.Logger: 配置好的日志记录器，包含文件与控制台两个 handler
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    # 文件 handler：详细记录到 test/log/<name>.log
    log_file = os.path.join(LOG_DIR, f"{name}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logger.addHandler(file_handler)

    # 控制台 handler：输出 INFO 及以上级别，便于开发者实时观看
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)

    logger.propagate = False
    return logger


def ensure_config() -> None:
    """确保 assets/config.json 存在，缺失则创建默认配置

    多数后端模块依赖配置文件，导入测试前需保证其可用。
    """
    try:
        import libs.cfg_handle as cfg_handle
        cfg_handle.cfg_handle().check_cfg_file()
    except Exception:
        # 配置初始化失败不阻断测试加载，由具体测试用例决定是否跳过
        pass


# 模块导入时自动确保配置文件就绪
ensure_config()
