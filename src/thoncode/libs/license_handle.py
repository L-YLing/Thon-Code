# libs/license_handle.py

import os
import shutil
from typing import Optional, Dict, List, Any


class LicenseHandle:
    """Handle license operations for projects"""
    
    def __init__(self):
        self.license_dir = "assets/git/license"
    
    def get_available_licenses(self) -> List[str]:
        """Get list of available license templates"""
        if not os.path.exists(self.license_dir):
            return []
        
        licenses = []
        for file in os.listdir(self.license_dir):
            if file.endswith('.md'):
                licenses.append(file[:-3])
        return sorted(licenses)
    
    def get_license_content(self, license_name: str) -> Optional[str]:
        """Get content of a license template"""
        license_path = os.path.join(self.license_dir, f"{license_name}.md")
        if not os.path.exists(license_path):
            return None
        
        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None
    
    def get_license_path(self, license_name: str) -> Optional[str]:
        """Get full path of license template"""
        path = os.path.join(self.license_dir, f"{license_name}.md")
        return path if os.path.exists(path) else None
    
    def add_license(self, license_name: str, content: str) -> bool:
        """Add a new license template"""
        if not license_name:
            return False
        
        os.makedirs(self.license_dir, exist_ok=True)
        license_path = os.path.join(self.license_dir, f"{license_name}.md")
        try:
            with open(license_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False
    
    def delete_license(self, license_name: str) -> bool:
        """Delete a license template"""
        license_path = os.path.join(self.license_dir, f"{license_name}.md")
        if not os.path.exists(license_path):
            return False
        try:
            os.remove(license_path)
            return True
        except Exception:
            return False
    
    def apply_license_to_project(self, project_root: str, license_name: str, 
                                  custom_vars: Optional[Dict[str, str]] = None) -> bool:
        """
        Apply a license to a project
        
        Args:
            project_root: Root directory of the project
            license_name: Name of the license to apply
            custom_vars: Custom variables to replace in template (e.g., {'year': '2024', 'author': 'Name'})
        """
        content = self.get_license_content(license_name)
        if not content:
            return False
        
        # Replace template variables
        if custom_vars:
            for key, value in custom_vars.items():
                content = content.replace(f'[{key}]', value)
                content = content.replace(f'{{{{{key}}}}}', value)
        
        # Write LICENSE file to project root
        license_file = os.path.join(project_root, "LICENSE")
        try:
            with open(license_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False
    
    def read_project_license(self, project_root: str) -> Optional[str]:
        """Read LICENSE file from project root"""
        license_file = os.path.join(project_root, "LICENSE")
        if not os.path.exists(license_file):
            return None
        try:
            with open(license_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None