import os
import sys
import json
import ctypes
import keyboard

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

def hide_from_taskbar(window):
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000

    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ex_style = ex_style & ~WS_EX_APPWINDOW | WS_EX_TOOLWINDOW
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
    ctypes.windll.user32.ShowWindow(hwnd, 5)
    ctypes.windll.user32.SetWindowPos(hwnd, None, 0, 0, 0, 0,
                                      0x0001 | 0x0002 | 0x0020 | 0x0040)

def previous_track(): keyboard.send("previous track")
def resume_pause_track(): keyboard.send("play/pause")
def next_track(): keyboard.send("next track")