import os
import sys
import json

def file_path(relative_path):
    try:
        base_path = sys._MEIPASS  # work as .exe
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))  # current file folder
    return os.path.join(base_path, relative_path)

def get_data_path(filename: str) -> str:
    if os.name == "nt":  # for windows i guess
        base = os.path.join(os.getenv("APPDATA") or os.getenv("LOCALAPPDATA"), "rwp-PythonSpotifyOverlay")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config", "rwp-PythonSpotifyOverlay")

    os.makedirs(base, exist_ok=True)  # create, if none exists
    return os.path.join(base, filename)

def get_data_dir() -> str:
    if os.name == "nt":
        base = os.path.join(os.getenv("APPDATA") or os.getenv("LOCALAPPDATA"), "rwp-PythonSpotifyOverlay")
    else:
        base = os.path.join(os.path.expanduser("~"), ".config", "rwp-PythonSpotifyOverlay")

    os.makedirs(base, exist_ok=True)
    return base

def load_settings():
    try:
        with open(get_data_path("settings.json"), "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_settings(data):
    print("Settings saved.")
    with open(get_data_path("settings.json"), "w") as f:
        json.dump(data, f, indent=4)