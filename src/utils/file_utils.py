"""
File utilities
"""

import os
import shutil
from datetime import datetime

def backup_file(file_path, backup_dir="backups"):
    """Create backup of file"""
    if not os.path.exists(file_path):
        return None
    
    os.makedirs(backup_dir, exist_ok=True)
    
    basename = os.path.basename(file_path)
    name, ext = os.path.splitext(basename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{name}_{timestamp}{ext}"
    backup_path = os.path.join(backup_dir, backup_name)
    
    shutil.copy(file_path, backup_path)
    return backup_path

def ensure_dir(path):
    """Ensure directory exists"""
    os.makedirs(path, exist_ok=True)
    return path

def clean_temp_files(directory, pattern="temp_*"):
    """Clean temporary files"""
    import glob
    
    temp_files = glob.glob(os.path.join(directory, pattern))
    for temp_file in temp_files:
        try:
            os.remove(temp_file)
        except:
            pass
    
    return len(temp_files)
