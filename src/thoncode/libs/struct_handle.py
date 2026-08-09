#! /usr/bin/env python3

import os
import json
import argparse
from typing import Union, Optional, Dict, List, Any

package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code",
    "Path": ".main.libs.struct_handle",
    "Entrance": "main.py"
}

import libs.cfg_handle as cfg_handle

DEFAULT_LANGS_PATH: str = "assets/langs/"

class langs_handle:
    def __init__(self) -> None:
        pass

    def default_language(self) -> dict:
        try:
            cfg_langs: str = cfg_handle.cfg_handle().read_cfg()["data"]["language"]
            return_msg: dict = {
                "status": "success",
                "data": cfg_langs,
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

    def key_languages(self, key: str = "") -> dict:
        try:
            LANGS_JSON:str = self.default_language()["data"]
            LANGS_PATH:str = DEFAULT_LANGS_PATH + LANGS_JSON + ".json"
            JSON_DATA = cfg_handle.cfg_handle(LANGS_PATH).read_cfg()["data"][key]
            return_msg: dict = {
                "status": "success",
                "data": JSON_DATA,
                "code": 200
            }
        except Exception as e:
            return_msg = {
                "status": "error",
                "data": str(e),
                "code": 405
            }
            return return_msg
        return return_msg

    def load_full_language(self) -> dict:
        try:
            lang = self.default_language()["data"]
            path = DEFAULT_LANGS_PATH + lang + ".json"
            full_data = cfg_handle.cfg_handle(path).read_cfg()["data"]
            return full_data
        except Exception as e:
            return {}

# Directory Structure Output Function

def get_dir_structure(
    root_path: str,
    output_format: str = "str",  # "str" | "json"
    output_file: Optional[str] = None,
    max_depth: int = -1,
    include_file_content: bool = False,
    content_file_exts: List[str] = ['.py']
) -> Union[str, Dict[str, Any]]:
    """
    Get the structure of a specified directory with multiple output formats.

    Parameters:
        root_path (str): The root directory path to scan.
        output_format (str): Output format, "str" for human-readable tree, "json" for structured data.
        output_file (Optional[str]): If specified, write the output to this file.
        max_depth (int): Recursion depth, -1 for unlimited, 0 for root only.
        include_file_content (bool): Whether to include file content (only for specified extensions).
        content_file_exts (List[str]): List of file extensions to include content for (default ['.py']).

    Returns:
        Union[str, Dict[str, Any]]: Returns string or dictionary based on output_format.
    """
    def _scan_dir(path: str, current_depth: int = 0) -> Dict[str, Any]:
        """Recursively scan a directory and return structured data."""
        if max_depth != -1 and current_depth > max_depth:
            return {"type": "dir", "name": os.path.basename(path), "children": []}

        result = {
            "type": "dir" if os.path.isdir(path) else "file",
            "name": os.path.basename(path),
            "path": os.path.abspath(path)
        }

        if os.path.isdir(path):
            children = []
            try:
                items = os.listdir(path)
                items.sort()  # Keep sorted for predictable output
                for item in items:
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        # Recursively scan subdirectories
                        children.append(_scan_dir(item_path, current_depth + 1))
                    else:
                        # Handle files with optional content extraction
                        file_info = {
                            "type": "file",
                            "name": item,
                            "path": os.path.abspath(item_path)
                        }
                        if include_file_content:
                            ext = os.path.splitext(item)[1]
                            if ext in content_file_exts:
                                try:
                                    with open(item_path, 'r', encoding='utf-8') as f:
                                        file_info["content"] = f.read()
                                except Exception as e:
                                    file_info["content"] = f"[Error reading file: {e}]"
                        children.append(file_info)
                result["children"] = children
            except PermissionError:
                result["children"] = []
                result["error"] = "Permission denied"
        else:
            # Handle file content if requested
            if include_file_content:
                ext = os.path.splitext(path)[1]
                if ext in content_file_exts:
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            result["content"] = f.read()
                    except Exception as e:
                        result["content"] = f"[Error reading file: {e}]"
            result["children"] = []  # Files have no children

        return result

    def _dict_to_tree(data: Dict[str, Any], prefix: str = "", is_last: bool = True) -> str:
        """Convert structured dictionary to tree string."""
        lines = []
        name = data.get("name", "")
        if data.get("type") == "dir":
            connector = "└── " if is_last else "├── "
            lines.append(prefix + connector + name + "/")
            children = data.get("children", [])
            if children:
                child_prefix = prefix + ("    " if is_last else "│   ")
                for i, child in enumerate(children):
                    is_last_child = (i == len(children) - 1)
                    lines.append(_dict_to_tree(child, child_prefix, is_last_child))
        else:
            connector = "└── " if is_last else "├── "
            file_line = prefix + connector + name
            if "content" in data:
                file_line += " (content included)"
            lines.append(file_line)
        return "\n".join(lines)

    # Verify root path exists
    if not os.path.exists(root_path):
        raise FileNotFoundError(f"Path does not exist: {root_path}")

    # Scan directory
    root_data = _scan_dir(root_path)

    if output_format == "str":
        # Human-readable tree structure
        result_str = _dict_to_tree(root_data)
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result_str)
        return result_str
    elif output_format == "json":
        # JSON structured output
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(root_data, f, indent=2, ensure_ascii=False)
        return root_data
    else:
        raise ValueError(f"Unsupported output format: {output_format}")