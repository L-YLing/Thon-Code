# export_structure.py
import os
import json
import time
from pathlib import Path

def should_ignore(path: Path) -> bool:
    """忽略不需要的目录/文件"""
    ignore_names = {'.venv', '__pycache__', '.git', '.idea', '.vscode', 'node_modules', 'dist', 'build'}
    if path.name in ignore_names:
        return True
    # 忽略隐藏文件（以.开头）
    if path.name.startswith('.'):
        return True
    return False

def get_structure(root_dir: Path, include_content: bool = True) -> dict:
    """递归获取目录结构，返回字典"""
    if should_ignore(root_dir):
        return None

    info = {
        "name": root_dir.name,
        "path": str(root_dir.absolute()),
        "type": "directory",
        "children": []
    }

    try:
        items = sorted(root_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    except PermissionError:
        return info

    for item in items:
        if should_ignore(item):
            continue
        if item.is_dir():
            child = get_structure(item, include_content)
            if child:
                info["children"].append(child)
        else:
            file_info = {
                "name": item.name,
                "path": str(item.absolute()),
                "type": "file",
                "size": item.stat().st_size,
                "mtime": time.ctime(item.stat().st_mtime)
            }
            if include_content and item.suffix in ('.py', '.json', '.txt', '.md', '.js', '.html', '.css'):
                try:
                    with open(item, 'r', encoding='utf-8') as f:
                        file_info["content"] = f.read()
                except:
                    file_info["content"] = "<无法读取>"
            info["children"].append(file_info)
    return info

if __name__ == "__main__":
    project_root = Path(__file__).parent
    output_file = project_root / "project_structure.json"
    print(f"正在导出项目结构到 {output_file} ...")
    structure = get_structure(project_root, include_content=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)
    print("导出完成。")