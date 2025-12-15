"""
Path utilities for handling data directories in both development and packaged app modes.
"""
import os
import sys
from pathlib import Path

def get_base_dir():
    """
    Get the base directory for the application.
    In development: returns the project root
    In PyInstaller bundle: returns the _internal directory
    """
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        return Path(sys._MEIPASS)
    else:
        # Running in development
        return Path(__file__).parent.parent

def get_data_dir():
    """
    Get the data directory for writable application data.
    In development: returns PROJECT_ROOT/data
    In packaged app: returns user's app data directory
    """
    if getattr(sys, 'frozen', False):
        # Running in packaged app - use user's Application Support directory
        if sys.platform == 'darwin':  # macOS
            data_dir = Path.home() / 'Library' / 'Application Support' / 'BookReconciler' / 'data'
        elif sys.platform == 'win32':  # Windows
            app_data = os.getenv('APPDATA')
            data_dir = Path(app_data) / 'BookReconciler' / 'data'
        else:  # Linux
            data_dir = Path.home() / '.bookreconciler' / 'data'

        # Create directory if it doesn't exist
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    else:
        # Running in development - use project data directory
        return get_base_dir() / 'data'

def get_hathi_data_dir():
    """Get the HathiTrust-specific data directory"""
    hathi_dir = get_data_dir() / 'hathi'
    hathi_dir.mkdir(parents=True, exist_ok=True)
    return hathi_dir

def get_cache_dir():
    """Get the cache directory for temporary reconciliation data"""
    cache_dir = get_data_dir() / 'cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

# Export as string for backward compatibility with f-string usage
CACHE_DIR = str(get_cache_dir())
