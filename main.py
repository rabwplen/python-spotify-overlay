import sys
import os
import threading
from pathlib import Path

import customtkinter as ctk

from overlay import Overlay
from spotify import setup_spotify
from utils import file_path, get_data_path

if __name__ == "__main__":
    # spotify setup (authorization)
    sp = setup_spotify()

    # creating and launching an application
    app = Overlay(sp)
    app.iconbitmap(file_path("assets/app-icon.ico"))

    threading.Thread(target=app.create_tray, daemon=True).start()

    app.mainloop()