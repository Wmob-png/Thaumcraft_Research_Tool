# resources.py
# Helper to find assets in both development and bundled exe

import sys
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def asset_path(filename):
    return resource_path(os.path.join("assets", filename))