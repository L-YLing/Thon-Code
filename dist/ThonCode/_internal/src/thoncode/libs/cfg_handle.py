#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code",
    "Path": ".main.libs.cfg_handle",
    "Entrance": "main.py"
}

import json
import os
import sys
import libs.json_handle as json_handle

DEFAULT_CFG_FILE_PATH: str = "assets/config.json"
DEFAULT_CFG_DATA: dict = {
    "language": "zh_cn",
    "theme": "dark",
    "auto_save": True,
    "auto_save_time_sec": 15,
    "tab_size": 4,
    "font_ligatures": True
}

class cfg_handle:
    def __init__(self, 
        cfg_file_path: str = DEFAULT_CFG_FILE_PATH) -> None:

        self.cfg_file_path = cfg_file_path
        return None

    def make_cfg_file(self, default_data: dict = DEFAULT_CFG_DATA) -> dict:
        try:
            with open(self.cfg_file_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(default_data, ensure_ascii=False, indent=4))

                return_msg = {
                    "status": "success",
                    "data": f"Configuration file created successfully at {self.cfg_file_path}.",
                    "code": 200
                }
            return return_msg
        except Exception as e:
            return_msg = {
                "status": "error",
                "data": str(e),
                "code": 405
            }
            return return_msg

    def check_cfg_file(self) -> dict:
        try:
            if os.path.exists(self.cfg_file_path):
                return_msg = {
                    "status": "success",
                    "data": f"Configuration file exists: {self.cfg_file_path}",
                    "code": 201
                }
                return return_msg
            else:
                self.make_cfg_file()
                return_msg = {
                    "status": "success",
                    "data": f"None",
                    "code": 200
                }
                return return_msg
        except Exception as e:
            return_msg = {
                "status": "error",
                "data": str(e),
                "code": 405
            }

    def read_cfg(self) -> dict:
        with open(self.cfg_file_path, "r", encoding="utf-8") as f:
            return_msg = {
                "status": "success",
                "data": json.load(f),
                "code": 200
            }
        return return_msg

    def write_cfg(self, data: dict) -> dict:
        try:
            with open(self.cfg_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return {"status": "success", "data": "配置已保存", "code": 200}
        except Exception as e:
            return {"status": "error", "data": str(e), "code": 405}

    def get_project_config(self, project_path):
        """读取项目根目录下的 .thoncode/project.json 配置，若无则返回默认"""
        config_dir = os.path.join(project_path, ".thoncode")
        config_file = os.path.join(config_dir, "project.json")
        default = {
            "python_path": sys.executable,   # 项目专用解释器
            "dependencies": []               # 从 requirements.txt 读取的依赖列表
        }
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 合并默认值，保证字段存在
                for key in default:
                    if key not in data:
                        data[key] = default[key]
                return data
        else:
            # 尝试读取 requirements.txt 初始化依赖
            req_file = os.path.join(project_path, "requirements.txt")
            deps = []
            if os.path.exists(req_file):
                with open(req_file, "r", encoding="utf-8") as f:
                    deps = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            default["dependencies"] = deps
            # 自动创建配置文件
            os.makedirs(config_dir, exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=4, ensure_ascii=False)
            return default

    def save_project_config(self, project_path, config):
        """保存项目配置到 .thoncode/project.json"""
        config_dir = os.path.join(project_path, ".thoncode")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "project.json")
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    def get_recent_projects(self, limit=10):
        """从全局配置读取最近项目列表"""
        cfg = self.read_cfg()["data"]
        return cfg.get("recent_projects", [])[:limit]

    def add_recent_project(self, project_path):
        """添加项目到最近列表（去重、置顶）"""
        cfg = self.read_cfg()["data"]
        recent = cfg.get("recent_projects", [])
        if project_path in recent:
            recent.remove(project_path)
        recent.insert(0, project_path)
        # 保持数量限制（例如10个）
        if len(recent) > 10:
            recent = recent[:10]
        cfg["recent_projects"] = recent
        self.write_cfg(cfg)