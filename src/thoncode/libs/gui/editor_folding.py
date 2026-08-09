class EditorFolding:
    def __init__(self, parent):
        self.parent = parent
        self._folded_lines = {}

    def _get_foldable_regions(self):
        if self.parent.language != "python":
            return []
        
        content = self.parent._textbox.get("1.0", "end-1c")
        lines = content.splitlines()
        fold_regions = []
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if stripped.startswith('def ') or stripped.startswith('async def '):
                base_indent = len(line) - len(line.lstrip(' '))
                end_line = self._find_block_end(lines, i, base_indent + 4)
                if end_line > i:
                    fold_regions.append((i, end_line))
            
            elif stripped.startswith('class '):
                base_indent = len(line) - len(line.lstrip(' '))
                end_line = self._find_block_end(lines, i, base_indent + 4)
                if end_line > i:
                    fold_regions.append((i, end_line))
        
        return fold_regions

    def _find_block_end(self, lines, start_line, min_indent):
        if start_line >= len(lines):
            return start_line
        
        for i in range(start_line, len(lines)):
            line = lines[i]
            if not line.strip():
                continue
            
            indent = len(line) - len(line.lstrip(' '))
            
            if indent < min_indent:
                return i
        
        return len(lines)

    def toggle_fold(self, line_num):
        if line_num in self._folded_lines:
            self._folded_lines.pop(line_num)
            self.parent._textbox.edit_modified(False)
            self.parent._update_line_numbers()
            self.parent.highlight_all()
        else:
            fold_regions = self._get_foldable_regions()
            for start, end in fold_regions:
                if start == line_num and end > start + 1:
                    self._folded_lines[start] = end
                    self.parent._textbox.edit_modified(False)
                    self.parent._update_line_numbers()
                    self.parent.highlight_all()
                    break