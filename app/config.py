"""Application configuration: paths, directories, and theme setup."""

import os
import platform
import customtkinter as ctk

# --- THEME CONFIG ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# --- APP DATA PATHS ---
if platform.system() == "Windows":
    APP_DIR = os.path.join(os.environ["LOCALAPPDATA"], "GalleryPlus")
else:
    APP_DIR = os.path.join(os.path.expanduser("~"), ".GalleryPlus")

THUMBS_DIR = os.path.join(APP_DIR, "thumbnails")
DB_PATH = os.path.join(APP_DIR, "faces.db")

# Create directories
os.makedirs(THUMBS_DIR, exist_ok=True)
