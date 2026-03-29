import os
import PyInstaller.__main__
import customtkinter
import face_recognition_models

# Get the directory paths for packages that have required data files (.json, .ttf, .dat)
customtkinter_path = os.path.dirname(customtkinter.__file__)
frm_path = os.path.dirname(face_recognition_models.__file__)

# Format the add-data strings based on the OS (Windows uses ';' separator)
separator = ';' if os.name == 'nt' else ':'
ctk_data = f"{customtkinter_path}{separator}customtkinter"
frm_data = f"{frm_path}{separator}face_recognition_models"

print("Starting PyInstaller build...")
print(f"Including CustomTkinter from: {customtkinter_path}")
print(f"Including Face Recognition Models from: {frm_path}")

PyInstaller.__main__.run([
    'main.py',                      # Primary script
    '--name=Gallery+',              # Name of output EXE/folder
    '--onedir',                     # Create a folder containing EXE and dependencies
    '--windowed',                   # Hide terminal console when app runs
    f'--add-data={ctk_data}',       # Bundle CustomTkinter themes and fonts
    f'--add-data={frm_data}',       # Bundle the heavy dlib machine learning models
    '--clean',                      # Clean PyInstaller cache before building
    '--noconfirm',                  # Replace output dir if it already exists without prompting
])

print("\n--- BUILD COMPLETE ---")
print("You can find the packaged application in the 'dist/Gallery+' folder.")
