#! /usr/bin/env python3

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code",
    "Path": ".main.libs.cfg_handle",
    "Entrance": "main.py"
}

import json
import os
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