#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Python注释删除工具
功能：删除Python源文件中的所有注释（单行注释、多行注释、文档字符串）
使用tokenize模块进行精确解析
"""

import tokenize
import io
import os
import sys
from pathlib import Path


class PythonCommentRemover:
    """Python注释删除器 - 使用tokenize模块精确解析"""
    
    def __init__(self, keep_shebang=True):
        """
        初始化
        
        Args:
            keep_shebang: 是否保留shebang行
        """
        self.keep_shebang = keep_shebang
    
    def remove_comments(self, content):
        """
        删除Python代码中的注释
        
        Args:
            content: Python源代码字符串
            
        Returns:
            删除注释后的代码字符串
        """
        try:
            # 使用tokenize模块解析
            tokens = []
            prev_end_line = 1
            prev_end_col = 0
            
            # 将内容转换为字节流
            content_bytes = content.encode('utf-8')
            source = io.BytesIO(content_bytes)
            
            # 获取所有token
            for token in tokenize.tokenize(source.readline):
                # token类型: COMMENT, STRING, NL, NEWLINE, INDENT, DEDENT等
                if token.type == tokenize.COMMENT:
                    # 跳过注释
                    continue
                elif token.type == tokenize.STRING:
                    # 检查是否是文档字符串（多行字符串）
                    # 文档字符串通常是模块、类或函数的第一条语句
                    # 我们保留所有非文档字符串的字符串
                    # 对于文档字符串，检查其位置
                    if self._is_docstring(token, tokens):
                        # 跳过文档字符串
                        continue
                    else:
                        # 保留普通字符串
                        tokens.append(token)
                else:
                    # 保留其他所有token
                    tokens.append(token)
            
            # 重建源代码
            result = self._reconstruct_source(tokens)
            return result
            
        except Exception as e:
            # 如果tokenize失败，使用简单方法
            print(f"⚠️  使用备用方法处理: {e}")
            return self._remove_comments_simple(content)
    
    def _is_docstring(self, token, tokens):
        """
        判断一个字符串token是否是文档字符串
        """
        # 文档字符串必须是字符串字面量
        if token.type != tokenize.STRING:
            return False
        
        # 检查字符串内容（去引号）
        text = token.string
        # 检查是否是三重引号字符串（文档字符串必须是三重引号）
        if not (text.startswith('"""') or text.startswith("'''")):
            return False
        
        # 检查位置：文档字符串通常在模块、类或函数的开头
        # 简单判断：如果前面没有其他语句（除了缩进），就是文档字符串
        # 这里简化处理：检查token之前的token
        # 如果是第一个token，或者是缩进后的第一个token，可能是文档字符串
        if not tokens:
            # 第一个token就是文档字符串
            return True
        
        # 检查前一个token
        last_token = tokens[-1]
        # 如果前一个token是NEWLINE或INDENT，可能是文档字符串
        if last_token.type in (tokenize.NEWLINE, tokenize.INDENT):
            return True
        
        return False
    
    def _reconstruct_source(self, tokens):
        """
        从tokens重建源代码
        """
        if not tokens:
            return ''
        
        lines = []
        current_line = 1
        current_col = 0
        
        for token in tokens:
            # 处理行号变化
            if token.start[0] > current_line:
                # 添加空行
                for _ in range(current_line, token.start[0]):
                    lines.append('')
                current_line = token.start[0]
                current_col = 0
            
            # 处理缩进
            if token.start[1] > current_col:
                lines[-1] += ' ' * (token.start[1] - current_col)
                current_col = token.start[1]
            elif token.start[1] < current_col:
                # 缩进减少，需要调整（简化处理）
                pass
            
            # 添加token文本
            lines[-1] += token.string
            current_col += len(token.string)
            
            # 更新当前行
            if token.end[0] > token.start[0]:
                current_line = token.end[0]
                current_col = token.end[1]
        
        return '\n'.join(lines)
    
    def _remove_comments_simple(self, content):
        """
        简单方法删除注释（备用）
        """
        lines = content.split('\n')
        result = []
        in_multiline = False
        in_docstring = False
        multiline_delimiter = None
        
        for line in lines:
            # 简单的多行注释处理
            if in_multiline or in_docstring:
                if multiline_delimiter in line:
                    # 检查是否结束
                    parts = line.split(multiline_delimiter, 1)
                    if len(parts) == 2:
                        in_multiline = False
                        in_docstring = False
                        # 保留后面的代码
                        if parts[1].strip():
                            result.append(parts[1])
                continue
            
            # 检查单行注释
            comment_pos = -1
            in_string = False
            in_single = False
            in_double = False
            escape = False
            
            for i, char in enumerate(line):
                if escape:
                    escape = False
                    continue
                if char == '\\':
                    escape = True
                    continue
                if char == "'" and not in_double:
                    in_single = not in_single
                elif char == '"' and not in_single:
                    in_double = not in_double
                elif char == '#' and not in_single and not in_double:
                    comment_pos = i
                    break
            
            if comment_pos != -1:
                line = line[:comment_pos]
            
            # 检查多行注释开始
            line_copy = line
            if '"""' in line_copy or "'''" in line_copy:
                # 检查是否是多行注释或文档字符串
                for delim in ['"""', "'''"]:
                    if delim in line_copy:
                        # 检查是否在同一行结束
                        parts = line_copy.split(delim)
                        if len(parts) >= 3:
                            # 在同一行开始和结束
                            line_copy = parts[0] + parts[2]
                        else:
                            # 开始多行注释
                            in_multiline = True
                            multiline_delimiter = delim
                            line_copy = parts[0]
                            break
            
            # 保留shebang
            if result or not line.startswith('#!'):
                if line_copy.strip() or line.strip() == '':
                    result.append(line_copy)
        
        return '\n'.join(result)
    
    def process_file(self, filepath, backup=True):
        """
        处理单个文件
        
        Args:
            filepath: 文件路径
            backup: 是否备份原文件
            
        Returns:
            bool: 是否成功
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            print(f"❌ 文件不存在: {filepath}")
            return False
        
        if not filepath.suffix == '.py':
            print(f"⚠️  跳过非Python文件: {filepath}")
            return False
        
        try:
            # 读取文件
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 删除注释
            new_content = self.remove_comments(content)
            
            # 检查是否有变化
            if content == new_content:
                print(f"ℹ️  没有变化: {filepath}")
                return True
            
            # 备份
            if backup:
                backup_path = filepath.with_suffix(filepath.suffix + '.bak')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"📦 已备份到: {backup_path}")
            
            # 写入新文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ 处理成功: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ 处理失败 {filepath}: {e}")
            return False
    
    def process_directory(self, directory, backup=True, recursive=True):
        """
        处理目录中的所有Python文件
        
        Args:
            directory: 目录路径
            backup: 是否备份
            recursive: 是否递归处理子目录
        """
        directory = Path(directory)
        
        if not directory.exists():
            print(f"❌ 目录不存在: {directory}")
            return
        
        if not directory.is_dir():
            print(f"❌ 不是目录: {directory}")
            return
        
        pattern = '**/*.py' if recursive else '*.py'
        py_files = list(directory.glob(pattern))
        
        if not py_files:
            print(f"ℹ️  没有找到Python文件: {directory}")
            return
        
        print(f"📂 找到 {len(py_files)} 个Python文件")
        print("-" * 50)
        
        success_count = 0
        for py_file in py_files:
            if self.process_file(py_file, backup):
                success_count += 1
        
        print("-" * 50)
        print(f"✅ 成功处理 {success_count}/{len(py_files)} 个文件")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='删除Python源文件中的所有注释（使用tokenize精确解析）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s script.py              # 删除 script.py 中的注释
  %(prog)s script.py --no-backup  # 不备份直接修改
  %(prog)s -d src/                # 处理 src/ 目录下所有 .py 文件
  %(prog)s -d src/ -n             # 处理目录但不递归子目录
        """
    )
    
    parser.add_argument(
        'file',
        nargs='?',
        help='要处理的Python文件路径'
    )
    
    parser.add_argument(
        '-d', '--directory',
        help='处理目录中的所有Python文件'
    )
    
    parser.add_argument(
        '-n', '--no-recursive',
        action='store_true',
        help='不递归处理子目录（仅当使用 -d 时有效）'
    )
    
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='不创建备份文件'
    )
    
    parser.add_argument(
        '--no-shebang',
        action='store_true',
        help='不保留shebang行'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    args = parser.parse_args()
    
    # 创建删除器
    remover = PythonCommentRemover(keep_shebang=not args.no_shebang)
    
    # 处理目录
    if args.directory:
        remover.process_directory(
            args.directory,
            backup=not args.no_backup,
            recursive=not args.no_recursive
        )
    # 处理文件
    elif args.file:
        remover.process_file(args.file, backup=not args.no_backup)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()