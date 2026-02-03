import os
import sys
import time
import json
import ctypes
import atexit
import requests
import textwrap
import keyboard
import threading
from pathlib import Path

import tkinter as tk
import customtkinter as ctk

import pystray
from pystray import MenuItem

from PIL import Image, ImageDraw, ImageTk
from io import BytesIO

import spotipy

from utils import file_path, get_data_path, save_settings, load_settings
from settings import SettingsWindow



# --- Application Control Functions ---
def quit_app(app):
    print("bye!")
    # completes all cycles so that the program closes completely
    if hasattr(app, "update_song_info_after_id") and app.update_song_info_after_id:
        app.after_cancel(app.update_song_info_after_id)

    if hasattr(app, "revert_timer") and app.revert_timer:
        app.revert_timer.cancel()

    # saving app window position
    geo = app.geometry()
    if "+" in geo:  # format type: '350x100+30+30'
        parts = geo.split("+")
        app_position_X = int(parts[1])
        app_position_Y = int(parts[2])
    else:
        app_position_X = app_position_Y = 30  # default

    save_settings({  # saves all settings and some data
        "default_opacity": app.default_opacity,
        "hover_opacity": app.hover_opacity,
        "fade_delay": app.fade_delay,
        "fade_duration": app.fade_duration,
        "always_on_top": app.always_on_top,
        "can_drag": app.can_drag,
        "click_through": app.click_through,
        "window_position_x": app_position_X,
        "window_position_y": app_position_Y
    })

    app.destroy()



# --- Window Manipulation Functions ---
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



# --- Image Processing Functions ---
def apply_gradient_alpha(image: Image.Image, direction: str = "left_to_right") -> Image.Image:
    w, h = image.size
    gradient = Image.new('L', (w, 1), color=0xFF)
    draw = ImageDraw.Draw(gradient)

    for x in range(w):
        alpha = int(255 * (x / w)) if direction == "left_to_right" else int(255 * ((w - x) / w))
        draw.point((x, 0), fill=alpha)

    alpha_mask = gradient.resize((w, h))
    image.putalpha(alpha_mask)
    return image



# --- Tray Functions ---
def create_tray(app):
    image = Image.open(file_path("assets/app-icon.png")).resize((32, 32))
    show_hide_text = "Hide Overlay" if not app.hidden else "Show Overlay"
    click_through_text = "Disable Click-Through" if app.click_through else "Enable Click-Through"

    global tray_icon
    tray_icon = pystray.Icon("spotify_overlay", image, "Spotify Overlay", menu=pystray.Menu(
        pystray.MenuItem(show_hide_text, lambda: tray_on_show_or_hide(app)),
        pystray.MenuItem("Open Settings", app.open_settings),
        pystray.MenuItem("Close App", lambda: quit_app(app))
    ))
    tray_icon.run()

def update_tray_menu(app):
    global tray_icon
    if tray_icon is None:
        return  # tray_icon not created yet

    show_hide_text = "Hide Overlay" if not app.hidden else "Show Overlay"

    tray_icon.menu = pystray.Menu(
        pystray.MenuItem(show_hide_text, lambda: tray_on_show_or_hide(app)),
        pystray.MenuItem("Open Settings", app.open_settings),
        pystray.MenuItem("Close App", lambda: quit_app(app))
    )
    tray_icon.update_menu()

def tray_on_show_or_hide(app):
    if app.hidden:
        app.deiconify()
    else:
        app.withdraw()
    app.hidden = not app.hidden
    update_tray_menu(app)

tray_icon = None








# !--- Main Overlay Class ---!

# UIs basic colors for Overlay
COLOR_BACKGROUND = "#000000"

# The Overlay
class Overlay(ctk.CTk):
    def __init__(self, sp):
        super().__init__()
        self.sp = sp
        self.settings = load_settings()

        # Changeable Variables
        # variables that are saved
        self.default_opacity = 0.6
        self.hover_opacity = 0.8
        self.fade_delay = 1
        self.fade_duration = 0.2
        self.inside = False
        self.revert_timer = None
        self.always_on_top = True
        self.can_drag = True
        self.click_through = False

        # variables that are not saved
        self.hidden = False

        # Extract the settings or use the default
        self.default_opacity = self.settings.get("default_opacity", 0.6)
        self.hover_opacity = self.settings.get("hover_opacity", 0.8)
        self.fade_delay = self.settings.get("fade_delay", 1)
        self.fade_duration = self.settings.get("fade_duration", 0.2)
        self.always_on_top = self.settings.get("always_on_top", True)
        self.can_drag = self.settings.get("can_drag", True)
        self.click_through = self.settings.get("click_through", False)
        app_position_X = self.settings.get("window_position_x", 30)
        app_position_Y = self.settings.get("window_position_y", 30)
        save_settings({
            "default_opacity": self.default_opacity,
            "hover_opacity": self.hover_opacity,
            "fade_delay": self.fade_delay,
            "fade_duration": self.fade_duration,
            "always_on_top": self.always_on_top,
            "can_drag": self.can_drag,
            "click_through": self.click_through
        })

        # Other Variables
        self.title("Spotify Overlay")
        self.geometry(f"350x80+{app_position_X}+{app_position_Y}")
        self.overrideredirect(True)
        # self.resizable(True, True) # useless
        self.attributes("-topmost", self.always_on_top)
        self.attributes("-alpha", self.default_opacity)
        self.after(250, lambda: hide_from_taskbar(self))
        self.set_click_through(self.click_through)

        self.settings_openned = False

        self.track_total_duration = None
        self.current_image_url = None

        self.can_update_song_info = True
        self.update_song_info_after_id = None

        # Create default album cover and default album cover with gradient
        self.default_album_cover = None
        self.default_album_cover_gradient = None
        default_album_cover_path = Path(file_path("assets/album-cover.jpeg"))

        if os.path.exists(default_album_cover_path):
            # Create a mask with rounded edges
            normal_image = Image.open(default_album_cover_path).resize((60, 60)).convert("RGBA")
            normal_mask = Image.new("L", (60, 60), 0)
            normal_draw = ImageDraw.Draw(normal_mask)
            normal_draw.rounded_rectangle((0, 0, 60, 60), radius=10, fill=255)
            normal_image.putalpha(normal_mask)

            # Create a mask with gradient
            gradient_image = Image.open(default_album_cover_path).resize((175, 175)).convert("RGBA")
            gradient_image = apply_gradient_alpha(gradient_image, direction="left_to_right")

            # Applying all masks for default album cover
            self.default_album_cover = ctk.CTkImage(light_image=normal_image, size=(60, 60))
            self.default_album_cover_gradient = ctk.CTkImage(light_image=gradient_image, size=(175, 175))
        else:
            print("!: album-cover.jpeg not found")

        # --- Commands ---
        def on_slider_change(value):
            new_position_ms = int((value / 100) * self.track_total_duration)

            self.spotify_track_duration.configure(text=f"{self.format_time(new_position_ms)} / {self.format_time(self.track_total_duration)}")

            try:
                self.sp.seek_track(new_position_ms)
            except spotipy.exceptions.SpotifyException as e:
                if "PREMIUM_REQUIRED" in str(e):
                    print("Rewind is only available for Spotify Premium.")
                else:
                    print("Another error when rewinding:", e)

        # ! --- UIs --- !
        
        # UIs Positions
        self.POS_close_button = {'relx': 0, 'rely': 0, 'x': 2, 'y': 2, "anchor": "nw"}
        self.POS_drag_button = {'relx': 0, 'rely': 1, 'x': 2, 'y': -2, "anchor": "sw"}
        self.POS_settings_button = {'relx': 0, 'rely': 0.5, 'x': 2, 'y': 0, "anchor": "w"}
        self.POS_spotify_title = {'relx': 0, 'rely': 0, 'x': 80, 'y': 3, "anchor": "nw"}
        self.POS_spotify_artist = {'relx': 0, 'rely': 0, 'x': 80, 'y': 25, "anchor": "nw"}
        self.POS_spotify_image = {'relx': 0, 'rely': 0.5, 'x': 5, 'y': 0, "anchor": "w"}
        self.POS_spotify_track_duration = {'relx': 0, 'rely': 1, 'x': 80, 'y': -2, "anchor": "sw"}
        self.POS_spotify_track_duration_slider = {'rely': 0.8, 'relx': 0.75, 'anchor': "ne"}
        self.POS_spotify_prev_track_button = {'relx': 1, 'rely': 1, 'x': -62, 'y': -2, "anchor": "se"}
        self.POS_spotify_pause_track_button = {'relx': 1, 'rely': 1, 'x': -32, 'y': -2, "anchor": "se"}
        self.POS_spotify_next_track_button = {'relx': 1, 'rely': 1, 'x': -2, 'y': -2, "anchor": "se"}

        # background for all window
        self.main_background = ctk.CTkFrame(self, fg_color=COLOR_BACKGROUND)
        self.main_background.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # track info frame
        self.background = ctk.CTkFrame(self, fg_color=COLOR_BACKGROUND, bg_color=COLOR_BACKGROUND, width=(self.winfo_width()-(26+4))) # or 26*2 for future
        self.background.place(relx=0, rely=.5, x=26, relheight=1, anchor="w")

        # Control Panel For 3-rd size mode
        self.control_frame = ctk.CTkFrame(self.background, fg_color="#000000")

        # close button
        self.close_icon = ctk.CTkImage(light_image=Image.open(file_path('assets/close-icon.png')), size=(10, 10))
        
        self.close_button = ctk.CTkButton(self.main_background, text="",
                                       width=22, height=22, corner_radius=0, image=self.close_icon,
                                       fg_color=COLOR_BACKGROUND, hover_color="#1A1A1A",
                                       command=lambda: quit_app(self))
        self.close_button.place(**self.POS_close_button)
        
        # drag button
        self.drag_icon = ctk.CTkImage(light_image=Image.open(file_path('assets/drag-icon.png')), size=(10, 10))

        self.drag_button = ctk.CTkButton(self.main_background, text="",
                                        width=22, height=22, corner_radius=0, image=self.drag_icon,
                                        fg_color=COLOR_BACKGROUND, hover_color=COLOR_BACKGROUND)
        self.drag_button.place(**self.POS_drag_button)
        self.drag_button.bind("<Button-1>", self.start_move)
        self.drag_button.bind("<B1-Motion>", self.on_motion)

        # settings button
        self.settings_icon = ctk.CTkImage(light_image=Image.open(file_path('assets/settings-icon.png')), size=(10, 10))

        self.settings_button = ctk.CTkButton(self.main_background, text="",
                                        width=22, height=22, corner_radius=0, image=self.settings_icon,
                                        fg_color=COLOR_BACKGROUND, hover_color="#1A1A1A",
                                        command=self.open_settings)
        self.settings_button.place(**self.POS_settings_button)

        # track title
        self.spotify_title = ctk.CTkLabel(self.background, text="", font=ctk.CTkFont(size=18, weight="bold", family="Arial"),
                                         text_color="#FFFFFF")
        self.spotify_title.place(**self.POS_spotify_title)

        # track artist
        self.spotify_artist = ctk.CTkLabel(self.background, text="", font=ctk.CTkFont(size=14, family="Arial"),
                                         text_color="#BEBEBE")
        self.spotify_artist.place(**self.POS_spotify_artist)

        # track image
        self.spotify_image = ctk.CTkLabel(self.background, text="")
        self.spotify_image.place(**self.POS_spotify_image)

        # track duration
        self.spotify_track_duration = ctk.CTkLabel(self.background, text="0:00 / 0:00", font=ctk.CTkFont(size=11, family="Arial"),
                                                   text_color="#BEBEBE")
        self.spotify_track_duration.place(**self.POS_spotify_track_duration)

        self.spotify_track_duration_progress = ctk.CTkLabel(self.background, text="0:00", font=ctk.CTkFont(size=13, family="Comic Sans"), text_color="light gray", height=12, fg_color="#000000")
        self.spotify_track_duration_total = ctk.CTkLabel(self.background, text="0:00", font=ctk.CTkFont(size=13, family="Comic Sans"), text_color="light gray", height=12, fg_color="#000000")

        self.spotify_track_duration_slider = ctk.CTkSlider(self.background, from_=0, to=100, state="disabled", command=on_slider_change,
                                                           width=110, height=10,
                                                           bg_color=COLOR_BACKGROUND, fg_color="#303030", progress_color="#FFFFFF",
                                                           button_color="#FFFFFF", button_hover_color="#FF0000")
        # self.spotify_track_duration_slider.place(**self.POS_spotify_track_duration_slider)

        # previous Track
        def previous_track():
            keyboard.send("previous track")

        self.spotify_prev_track_button = ctk.CTkButton(self.background, text="|◀", font=ctk.CTkFont(size=12),
                                                            width=25, height=25, corner_radius=5,
                                                            fg_color="#202020", hover_color="#3D3D3D", text_color="white",
                                                            command=previous_track)
        self.spotify_prev_track_button.place(**self.POS_spotify_prev_track_button)

        # resume/pause Track
        def resume_pause_track():
            keyboard.send("play/pause")

        self.spotify_pause_track_button = ctk.CTkButton(self.background, text="▶", font=ctk.CTkFont(size=13, weight="bold"),
                                                            width=25, height=25, corner_radius=5,
                                                            fg_color="#FFF", hover_color="light gray", text_color="#202020",
                                                            command=resume_pause_track)
        self.spotify_pause_track_button.place(**self.POS_spotify_pause_track_button)

        # next Track
        def next_track():
            keyboard.send("next track")

        self.spotify_next_track_button = ctk.CTkButton(self.background, text="▶|", font=ctk.CTkFont(size=12),
                                                            width=25, height=25, corner_radius=5,
                                                            fg_color="#202020", hover_color="#3D3D3D", text_color="white",
                                                            command=next_track)
        self.spotify_next_track_button.place(**self.POS_spotify_next_track_button)

        # other
        self.monitor_mouse()
        self.start_update_loop()
        self.settings_toggle_click_through()
    
    def set_click_through(window, enable: bool):
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_LAYERED = 0x00080000

        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

        if enable:
            styles |= WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:
            styles &= ~WS_EX_TRANSPARENT

        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles)

    def start_update_loop(self):
        def background_loop():
            while self.can_update_song_info:
                try:
                    current = self.sp.current_playback()
                    self.after(0, lambda: self.update_song_info(current))
                except Exception as e:
                    print(f"Update error: {e}")
                time.sleep(0.35)

        threading.Thread(target=background_loop, daemon=True).start()

    def format_time(self, ms):
        seconds = int(ms / 1000)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"

    def update_song_info(self, current=None):
        if current is None:
            try:
                current = self.sp.current_playback()
            except:
                print("what?")
                return

        if current and current["is_playing"]:
            track = current['item']
            title = track['name']
            middleTitle = textwrap.shorten(title, width=35, placeholder="...")
            shortTitle = textwrap.shorten(title, width=32, placeholder="...")
            shortestTitle = textwrap.shorten(title, width=30, placeholder="...")
            artist = track['artists'][0]['name']
            album = track['album'].get('name')
            track_duration = "0:00 / 0:00"
            images = track['album'].get('images', [])
            image_url = images[0]['url'] if images else None
            progress_ms = current["progress_ms"]
            duration_ms = current["item"]["duration_ms"]
            self.track_total_duration = duration_ms
            track_duration = f"{self.format_time(progress_ms)} / {self.format_time(duration_ms)}"

            # updates all label
            middle_spotify_title_new = f"{middleTitle}"
            if self.spotify_title.cget("text") != middle_spotify_title_new:
                print("Update < spotify_title > to < middleTitle >")
                self.spotify_title.configure(text=middle_spotify_title_new)

            spotify_artist_new = f"{artist}"
            if self.spotify_artist.cget("text") != spotify_artist_new:
                print("Update < spotify_artist > to < artist >")
                self.spotify_artist.configure(text=spotify_artist_new)

            if self.spotify_image.place_info() == {}:
                print("cho")
                self.spotify_image.place(**self.POS_spotify_image)

            self.spotify_track_duration.configure(text=track_duration)

            if self.spotify_pause_track_button.cget("text") != "||":
                print("Update < spotify_pause_track_button > to '||'")
                self.spotify_pause_track_button.configure(text="||", font=ctk.CTkFont(size=11, weight="bold"))


            # update slider
            if duration_ms > 0:
                slider_value = (progress_ms / duration_ms) * 100
                self.spotify_track_duration_slider.set(slider_value)

            # get image
            def update_album_cover(image_url):
                if not image_url:
                    if self.spotify_image.cget("image") is not self.default_album_cover and self.spotify_image.cget("image") is not self.default_album_cover_gradient or self.current_image_url == "idk123":
                        print("Update < spotify_image > to default album cover < self.default_album_cover >")
                        self.spotify_image.configure(image=self.default_album_cover)
                        self.spotify_image.image = self.default_album_cover
                        self.current_image_url = None
                    return

                if image_url == self.current_image_url:
                    return  # same image, do nothing

                if image_url != self.current_image_url:
                    print("Update < spotify_image > to < image_url >")

                    self.current_image_url = image_url

                    response = requests.get(image_url, timeout=2)

                    image_data = Image.open(BytesIO(response.content)).resize((70, 70)).convert("RGBA")

                    mask = Image.new("L", (70, 70), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.rounded_rectangle((0, 0, 70, 70), radius=10, fill=255)
                    image_data.putalpha(mask)

                    final_image = ctk.CTkImage(light_image=image_data, size=(70, 70))
                    self.spotify_image.configure(image=final_image)
                    self.spotify_image.image = final_image

            update_album_cover(image_url)

        # else:  # if nothing is playing right now
        #     if self.title_label.cget("text") != "Paused." or self.spotify_pause_track_button.cget("text") != "▶":
        #         print("Update all ui elements to < 'non playing' >")
        #         self.title_label.configure(text="Paused.")
        #         self.spotify_pause_track_button.configure(text="▶", font=ctk.CTkFont(size=10))

    def settings_toggle_click_through(self):
        if self.click_through:
            self.close_button.place_forget()
            self.settings_button.place_forget()
            self.drag_button.place_forget()
        else:
            self.close_button.place(**self.POS_close_button)
            self.settings_button.place(**self.POS_settings_button)
            self.drag_button.place(**self.POS_drag_button)

    def create_tray(self):
        create_tray(self) # very important for tray (used in main.py)

    def open_settings(self):
        if getattr(self, "settings_openned", False):
            if hasattr(self, "settings_window") and self.settings_window.winfo_exists():
                self.settings_window.lift()
                self.settings_window.focus_force()
            return

        self.settings_openned = True
        self.settings_window = SettingsWindow(self) 

    def start_move(self, event):
        if self.can_drag:
            self._drag_start_x = self.winfo_pointerx() - self.winfo_x()
            self._drag_start_y = self.winfo_pointery() - self.winfo_y()

    def on_motion(self, event):
        if self.can_drag:
            new_x = self.winfo_pointerx() - self._drag_start_x
            new_y = self.winfo_pointery() - self._drag_start_y
            self.geometry(f"+{new_x}+{new_y}")

    def monitor_mouse(self):
        def check_loop():
            try:
                x, y = self.winfo_pointerx(), self.winfo_pointery()
                x0, y0 = self.winfo_rootx(), self.winfo_rooty()
                x1, y1 = x0 + self.winfo_width(), y0 + self.winfo_height()
                inside_now = x0 <= x <= x1 and y0 <= y <= y1

                if inside_now and not self.inside:
                    self.inside = True
                    self.on_enter()
                elif not inside_now and self.inside:
                    self.inside = False
                    self.on_leave()
            except tk.TclError:
                return

            self.after(50, check_loop)

        check_loop()

    def on_enter(self):
        if self.click_through == False:
            if self.revert_timer:
                self.revert_timer.cancel()
            self.fade_to(self.hover_opacity)

    def on_leave(self):
        if self.revert_timer:
            self.revert_timer.cancel()
        self.revert_timer = threading.Timer(self.fade_delay, lambda: self.fade_to(self.default_opacity))
        self.revert_timer.daemon = True
        self.revert_timer.start()

    def fade_to(self, target_opacity):
        current_opacity = self.attributes("-alpha")
        steps = 10
        step_size = (target_opacity - current_opacity) / steps
        delay = int(self.fade_duration * 1000 / steps)

        def fade_step(step=0):
            if step < steps:
                new_opacity = self.attributes("-alpha") + step_size
                self.attributes("-alpha", max(0.0, min(1.0, new_opacity)))
                self.after(delay, lambda: fade_step(step + 1))
            else:
                self.attributes("-alpha", target_opacity)

        fade_step()
    