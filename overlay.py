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

from utils import *
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
    if "+" in geo:
        parts = geo.split("+")
        app.app_position_X = int(parts[1])
        app.app_position_Y = int(parts[2])
    else:
        app.app_position_X = app.app_position_Y = 42  # default

    save_settings({  # saves all settings and some data
        "default_opacity": app.default_opacity,
        "hover_opacity": app.hover_opacity,
        "fade_delay": app.fade_delay,
        "fade_duration": app.fade_duration,
        "always_on_top": app.always_on_top,
        "can_drag": app.can_drag,
        "click_through": app.click_through,
        "window_position_x": app.app_position_X,
        "window_position_y": app.app_position_Y
    })

    app.destroy()



# --- Tray Functions ---
def create_tray(app):
    image = Image.open(file_path("assets/app-icon.png")).resize((32, 32))
    show_hide_text = "Hide Overlay" if not app.hidden else "Show Overlay"

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
COLOR_SECOND_BACKGROUND = "#080808"
COLOR_MAIN_TEXT = "#FFFFFF"
COLOR_SECONDARY_TEXT = "#BEBEBE"
COLOR_MUTED_TEXT = "#6E6E6E"
COLOR_CONTROL_PANEL = "#000000"

# Standard UIs Positions
POS_BACKGROUND = {'relx': 0, 'rely': 0, 'x': 26, 'y': 0, "anchor": "nw"}

POS_CLOSE_BUTTON = {'relx': 0, 'rely': 0, 'x': 2, 'y': 2, "anchor": "nw"}
POS_SETTINGS_BUTTON = {'relx': 0, 'rely': 0, 'x': 2, 'y': 28, "anchor": "nw"}
POS_DRAG_BUTTON = {'relx': 0, 'rely': 1, 'x': 2, 'y': -2, "anchor": "sw"}
POS_RESIZE_GRIP = {'relx': 1, 'rely': 1, 'x': 0, 'y': 0, "anchor": "se"}

POS_BUTTONS_FRAME = {'relx': 1, 'rely': 1, 'x': -30, 'y': -2, "anchor": "se"}
POS_PREV_TRACK_BUTTON = {'relx': 0, 'rely': .5, 'x': 0, 'y': 0, "anchor": "w"}
POS_PAUSE_TRACK_BUTTON = {'relx': .5, 'rely': .5, 'x': 0, 'y': 0, "anchor": "center"}
POS_NEXT_TRACK_BUTTON = {'relx': 1, 'rely': .5, 'x': 0, 'y': 0, "anchor": "e"}

POS_CONTROL_PANEL_FRAME = {'relx': 0, 'rely': 1, 'x': 26, 'y': 0, "anchor": "sw"}
POS_PREV_TRACK_BUTTON_CP = {'relx': .5, 'rely': 0, 'x': -40, 'y': 5, "anchor": "n"}
POS_PAUSE_TRACK_BUTTON_CP = {'relx': .5, 'rely': 0, 'x': 0, 'y': 5, "anchor": "n"}
POS_NEXT_TRACK_BUTTON_CP = {'relx': .5, 'rely': 0, 'x': 40, 'y': 5, "anchor": "n"}

POS_TRACK_TITLE = {'relx': 0, 'rely': 0, 'x': 80, 'y': 3, "anchor": "nw"}
POS_TRACK_ARTIST = {'relx': 0, 'rely': 0, 'x': 80, 'y': 23, "anchor": "nw"}
POS_TRACK_IMAGE = {'relx': 0, 'rely': 0.5, 'x': 5, 'y': 0, "anchor": "w"}

POS_TRACK_DURATION = {'relx': 0, 'rely': 1, 'x': 80, 'y': -1, "anchor": "sw"}
POS_TRACK_DURATION_SLIDER = {'relx': 0.5, 'rely': 1, 'x': 0, 'y': -11, "anchor": "s"}
POS_TRACK_DURATION_PROGRESS = {'relx': 0, 'rely': 1, 'x': 12, 'y': -2, "anchor": "sw"}
POS_TRACK_DURATION_TOTAL = {'relx': 1, 'rely': 1, 'x': -12, 'y': -2, "anchor": "se"}

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
        self.app_position_X = self.settings.get("window_position_x", 42)
        self.app_position_Y = self.settings.get("window_position_y", 42)
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
        self.geometry(f"350x80+{self.app_position_X}+{self.app_position_Y}")
        self.overrideredirect(True)
        # self.resizable(True, True) # useless
        self.attributes("-topmost", self.always_on_top)
        self.attributes("-alpha", self.default_opacity)
        self.after(250, lambda: hide_from_taskbar(self))
        self.set_click_through(self.click_through)
        self.MIN_WIDTH = 300
        self.MIN_HEIGHT = 55
        self.MAX_WIDTH = 1150
        self.MAX_HEIGHT = 630

        self.settings_openned = False

        self.track_total_duration = None
        self.current_image_url = None
        self.current_image_size = 0

        self.can_update_song_info = True
        self.update_song_info_after_id = None

        self.default_album_cover = None
        
        self._adjusting_layout = False
        
        self.window_w = self.winfo_width()
        self.window_w = self.winfo_height()
        
        self.current_window_w = 0
        self.current_window_h = 0

        # --- Commands ---
        def on_slider_change(value):
            new_position_ms = int((value / 100) * self.track_total_duration)

            self.track_duration.configure(text=f"{self.format_time(new_position_ms)} / {self.format_time(self.track_total_duration)}")

            try:
                self.sp.seek_track(new_position_ms)
            except spotipy.exceptions.SpotifyException as e:
                if "PREMIUM_REQUIRED" in str(e):
                    print("!: Rewind is only available for Spotify Premium.")
                else:
                    print("!: Another error when rewinding:", e)

        # ! --- UIs --- !

        # background for all window
        self.main_background = ctk.CTkFrame(self, fg_color=COLOR_BACKGROUND, bg_color="transparent")
        self.main_background.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # track info frame
        self.background = ctk.CTkFrame(self, fg_color=COLOR_BACKGROUND, bg_color=COLOR_BACKGROUND, height=self.winfo_height())
        self.background.place(**POS_BACKGROUND)

        # close button
        self.close_icon = ctk.CTkImage(light_image=Image.open(file_path('assets/close-icon.png')), size=(10, 10))
        
        self.close_button = ctk.CTkButton(self.main_background, text="",
                                       width=22, height=22, corner_radius=0, image=self.close_icon,
                                       fg_color=COLOR_BACKGROUND, hover_color="#1A1A1A",
                                       command=lambda: quit_app(self))
        self.close_button.place(**POS_CLOSE_BUTTON)
        
        # drag button
        self.drag_icon = ctk.CTkImage(light_image=Image.open(file_path('assets/drag-icon.png')), size=(10, 10))

        self.drag_button = ctk.CTkLabel(self.main_background, text="", image=self.drag_icon,
                                        width=22, height=22, 
                                        fg_color=COLOR_BACKGROUND)
        self.drag_button.place(**POS_DRAG_BUTTON)
        self.drag_button.bind("<Button-1>", self.start_move)
        self.drag_button.bind("<B1-Motion>", self.on_motion)

        # settings button
        self.settings_icon = ctk.CTkImage(light_image=Image.open(file_path('assets/settings-icon.png')), size=(10, 10))

        self.settings_button = ctk.CTkButton(self.main_background, text="", image=self.settings_icon,
                                        width=22, height=22, corner_radius=0,
                                        fg_color=COLOR_BACKGROUND, hover_color="#1A1A1A",
                                        command=self.open_settings)
        self.settings_button.place(**POS_SETTINGS_BUTTON)
        
        # resize grip
        self.resize_icon = ctk.CTkImage(light_image=Image.open(file_path('assets/resize-icon.png')), size=(16, 16))
        
        self.resize_grip = ctk.CTkLabel(self, text="", image=self.resize_icon,
                                        width=18, height=18,
                                        fg_color=COLOR_BACKGROUND)
        self.resize_grip.place(**POS_RESIZE_GRIP)
        self.resize_grip.configure(cursor="size_nw_se")
        self.resize_grip.bind("<Button-1>", self._on_resize_start)
        self.resize_grip.bind("<B1-Motion>", self._on_resizing)
        self.resize_grip.bind("<ButtonRelease-1>", self._on_resize_end)
        self.bind("<Configure>", self._on_configure)

        # track title
        self.track_title = ctk.CTkLabel(self.background, text="", font=ctk.CTkFont(size=18, weight="bold", family="Arial"),
                                         text_color=COLOR_MAIN_TEXT)
        self.track_title.place(**POS_TRACK_TITLE)

        # track artist
        self.track_artist = ctk.CTkLabel(self.background, text="", font=ctk.CTkFont(size=13, family="Arial"),
                                         text_color=COLOR_SECONDARY_TEXT)
        self.track_artist.place(**POS_TRACK_ARTIST)

        # track image
        self.track_image = ctk.CTkLabel(self.background, text="")
        self.track_image.place(**POS_TRACK_IMAGE)

        # track duration
        self.track_duration = ctk.CTkLabel(self.background, text="", font=ctk.CTkFont(size=11, family="Arial"), 
                                                   text_color=COLOR_SECONDARY_TEXT)
        self.track_duration.place(**POS_TRACK_DURATION) # text="0:00 / 0:00"

        # frame for track buttons
        self.buttons_frame = ctk.CTkFrame(self, fg_color=COLOR_BACKGROUND, bg_color=COLOR_BACKGROUND, width=90, height=25)
        self.buttons_frame.place(**POS_BUTTONS_FRAME)
        
        # previous track
        self.prev_track_button = ctk.CTkButton(self.buttons_frame, text="|◀", font=ctk.CTkFont(size=12),
                                                            width=25, height=25, corner_radius=5,
                                                            fg_color="#202020", hover_color="#3D3D3D", text_color="white",
                                                            command=previous_track)
        self.prev_track_button.place(**POS_PREV_TRACK_BUTTON)

        # resume/pause track
        self.pause_track_button = ctk.CTkButton(self.buttons_frame, text="▶", font=ctk.CTkFont(size=13, weight="bold"),
                                                            width=25, height=25, corner_radius=5,
                                                            fg_color="#FFF", hover_color="light gray", text_color="#202020",
                                                            command=resume_pause_track)
        self.pause_track_button.place(**POS_PAUSE_TRACK_BUTTON)

        # next track
        self.next_track_button = ctk.CTkButton(self.buttons_frame, text="▶|", font=ctk.CTkFont(size=12),
                                                            width=25, height=25, corner_radius=5,
                                                            fg_color="#202020", hover_color="#3D3D3D", text_color="white",
                                                            command=next_track)
        self.next_track_button.place(**POS_NEXT_TRACK_BUTTON)
        
        # control panel
        self.control_panel_frame = ctk.CTkFrame(self,
                                                width=(self.winfo_width()), height=60,
                                                fg_color=COLOR_CONTROL_PANEL, bg_color=COLOR_BACKGROUND)
        self.control_panel_frame.place(**POS_CONTROL_PANEL_FRAME)
        
        # previous track in control panel
        self.prev_track_button_cp = ctk.CTkButton(self.control_panel_frame, text="|◀", font=ctk.CTkFont(size=14),
                                                            width=28, height=28, corner_radius=5,
                                                            fg_color="#202020", hover_color="#3D3D3D", text_color="white",
                                                            command=previous_track)
        self.prev_track_button_cp.place(**POS_PREV_TRACK_BUTTON_CP)

        # resume/pause track  in control panel
        self.pause_track_button_cp = ctk.CTkButton(self.control_panel_frame, text="▶", font=ctk.CTkFont(size=15, weight="bold"),
                                                            width=28, height=28, corner_radius=5,
                                                            fg_color="#FFF", hover_color="light gray", text_color="#202020",
                                                            command=resume_pause_track)
        self.pause_track_button_cp.place(**POS_PAUSE_TRACK_BUTTON_CP)

        # next track  in control panel
        self.next_track_button_cp = ctk.CTkButton(self.control_panel_frame, text="▶|", font=ctk.CTkFont(size=14),
                                                            width=28, height=28, corner_radius=5,
                                                            fg_color="#202020", hover_color="#3D3D3D", text_color="white",
                                                            command=next_track)
        self.next_track_button_cp.place(**POS_NEXT_TRACK_BUTTON_CP)
        
        # track duration slider
        self.track_duration_slider = ctk.CTkSlider(self.control_panel_frame, from_=0, to=100, state="disabled", command=on_slider_change,
                                                           width=(self.winfo_width()), height=10,
                                                           bg_color=COLOR_CONTROL_PANEL, fg_color="#4d4d4d", progress_color="#FFFFFF",
                                                           button_color="#FFFFFF", button_hover_color="#4d4d4d")
        self.track_duration_slider.place(**POS_TRACK_DURATION_SLIDER)
        
        # track duration progress label
        self.track_duration_progress = ctk.CTkLabel(self.control_panel_frame, text="0:00", font=ctk.CTkFont(size=12, family="Comic Sans"),
                                                    text_color=COLOR_MUTED_TEXT, fg_color=COLOR_CONTROL_PANEL)
        self.track_duration_progress.place(**POS_TRACK_DURATION_PROGRESS)
        
        # track duration label
        self.track_duration_total = ctk.CTkLabel(self.control_panel_frame, text="0:00", font=ctk.CTkFont(size=12, family="Comic Sans"),
                                                 text_color=COLOR_MUTED_TEXT, fg_color=COLOR_CONTROL_PANEL)
        self.track_duration_total.place(**POS_TRACK_DURATION_TOTAL)
        
        
        # just text that is displayed if any track is not playing when the program starts
        self.start_label = ctk.CTkLabel(self.background, text="Nothing is playing on Spotify", font=ctk.CTkFont(size=15, weight="bold", family="Arial"),
                                         text_color=COLOR_MUTED_TEXT, fg_color=COLOR_BACKGROUND)
        self.start_label.place(relx=0.5, rely=0.5, anchor="center", relwidth=1, relheight=1) 

        # other
        self.monitor_mouse()
        self.start_update_loop()
        self.settings_toggle_click_through()
        self.after(100, self.adjust_layout)
        
        # ui layers
        self.track_artist.lift()
        self.track_title.lift()
        self.start_label.lift()
    
    
    
    def format_time(self, ms):
        seconds = int(ms / 1000)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
    
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
    
    def settings_toggle_click_through(self):
        if self.click_through:
            self.close_button.place_forget()
            self.settings_button.place_forget()
            self.drag_button.place_forget()
            # self.background.configure(bg_color="transparent")
            self.background.place_configure(relx=0, rely=0, x=2, anchor="nw")
        else:
            self.close_button.place(**POS_CLOSE_BUTTON)
            self.settings_button.place(**POS_SETTINGS_BUTTON)
            self.drag_button.place(**POS_DRAG_BUTTON)
            self.background.configure(bg_color=COLOR_BACKGROUND)
            self.background.place_configure(**POS_BACKGROUND)

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
            shorterTitle = textwrap.shorten(title, width=26, placeholder="-")
            artist = track['artists'][0]['name']
            track_duration = "0:00 / 0:00"
            images = track['album'].get('images', [])
            image_url = images[0]['url'] if images else None
            progress_ms = current["progress_ms"]
            duration_ms = current["item"]["duration_ms"]
            self.track_total_duration = duration_ms
            track_duration = f"{self.format_time(progress_ms)} / {self.format_time(duration_ms)}"

            # updates all label
            title_new = f"{title}"
            if self.track_title.cget("text") != title_new:
                if self.start_label.place_configure != {}:
                    self.start_label.place_forget()
                print("Update < track_title > to < title >")
                self.track_title.configure(text=title_new)

            artist_new = f"{artist}"
            if self.track_artist.cget("text") != artist_new:
                print("Update < track_artist > to < artist >")
                self.track_artist.configure(text=artist_new)

            if self.pause_track_button.cget("text") != "||":
                print("Update < pause_track_button > to '||'")
                self.pause_track_button.configure(text="||", font=ctk.CTkFont(size=11, weight="bold"))
                self.pause_track_button_cp.configure(text="||", font=ctk.CTkFont(size=14, weight="bold"))
            
            self.track_duration.configure(text=track_duration)
            self.track_duration_progress.configure(text=self.format_time(progress_ms))
            self.track_duration_total.configure(text=self.format_time(duration_ms))

            # update slider
            if duration_ms > 0:
                slider_value = (progress_ms / duration_ms) * 100
                self.track_duration_slider.set(slider_value)

            cover_size = self._get_cover_size()
            self.update_album_cover(image_url, cover_size)

        else:  # if nothing is playing right now
            if self.pause_track_button.cget("text") != "▶":
                print("Update < pause_track_button > to '▶'")
                self.pause_track_button.configure(text="▶", font=ctk.CTkFont(size=13))
                self.pause_track_button_cp.configure(text="▶", font=ctk.CTkFont(size=15, weight="bold"))
            
            cover_size = self._get_cover_size()
            # self.update_album_cover(None, cover_size)
            if self.current_image_size != cover_size:
                if self.current_image_url:
                    self.update_album_cover(self.current_image_url, cover_size)
                elif self.current_image_url is None and self.current_image_size != cover_size:
                    self.update_album_cover(None, cover_size)
    
    # get image
    def update_album_cover(self, image_url, image_size):
        if not image_url:
            if self.current_image_size != image_size or self.current_image_url is not None:
                print("Update < track_image > to default album cover < self.default_album_cover >")
                default_path = Path(file_path("assets/album-cover.png"))
                if default_path.exists():
                    img = Image.open(default_path).resize((image_size, image_size)).convert("RGBA")
                    mask = Image.new("L", (image_size, image_size), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.rounded_rectangle((0, 0, image_size, image_size), radius=10, fill=255)
                    img.putalpha(mask)
                    final_img = ctk.CTkImage(light_image=img, size=(image_size, image_size))
                    self.track_image.configure(image=final_img)
                    self.track_image.image = final_img
                self.current_image_size = image_size
                self.current_image_url = None
            return

        if image_url == self.current_image_url and image_size == self.current_image_size:
            return  # nothing has changed, do nothing.

        self.current_image_url = image_url
        self.current_image_size = image_size

        try:
            response = requests.get(image_url, timeout=2)
            response.raise_for_status()  # checking for errors
            image_data = Image.open(BytesIO(response.content)).resize((image_size, image_size)).convert("RGBA")

            mask = Image.new("L", (image_size, image_size), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, image_size, image_size), radius=10, fill=255)
            image_data.putalpha(mask)

            final_image = ctk.CTkImage(light_image=image_data, size=(image_size, image_size))
            self.track_image.configure(image=final_image)
            self.track_image.image = final_image
            print(f"Update < track_image > to < image_url > (size={image_size}; url={image_url})")
            
        except Exception as e:
            print(f"Error loading image: {e}")
            self.update_album_cover(None, image_size)
    
    def adjust_layout(self):
        if self._adjusting_layout:
            return
        
        self._adjusting_layout = True
        try:
            self.window_w = self.winfo_width()
            self.window_h = self.winfo_height()
            
            if self.current_window_w != self.window_w or self.current_window_h != self.window_h:
                self.current_window_w = self.window_w
                self.current_window_h = self.window_h
                
                # to make it easier to write code
                w = self.window_w
                h = self.window_h
                
                print(f"w={w} | h={h}")
                
                cover_size = self._get_cover_size()
                labels_x = cover_size + 15
                
                # basic ui configure that will change
                self.control_panel_frame.place_forget()
                self.background.configure(width=w-26, height=h, fg_color=COLOR_BACKGROUND)
                
                self.track_title.place_configure(**{**POS_TRACK_TITLE, 'x': labels_x})
                self.track_artist.place_configure(**{**POS_TRACK_ARTIST, 'x': labels_x})
                self.track_image.place(**POS_TRACK_IMAGE)
                
                self.track_duration.place_configure(**{**POS_TRACK_DURATION, 'x': labels_x})
                self.track_duration_slider.place_forget()
                
                self.settings_button.place(**POS_SETTINGS_BUTTON)
                self.buttons_frame.place(**POS_BUTTONS_FRAME)
                
                if h >= 340:
                    print(340)
                    self.control_panel_frame.place(**POS_CONTROL_PANEL_FRAME)
                    self.control_panel_frame.configure(width=w-26*2)
                    self.background.configure(width=w-26*2, height=(h - self.control_panel_frame.winfo_height()), fg_color=COLOR_SECOND_BACKGROUND)
                    
                    self.track_title.place_configure(relx=0, rely=1, x=2, y=-22, anchor="sw")
                    self.track_artist.place_configure(relx=0, rely=1, x=2, y=-2, anchor="sw")
                    self.track_image.place(relx=0.5, rely=0, x=0, y=15, anchor="n")
                    
                    self.track_duration.place_forget()
                    self.track_duration_slider.place(**POS_TRACK_DURATION_SLIDER)
                    self.track_duration_slider.configure(width=(self.control_panel_frame.winfo_width()-84))
                    # self.track_duration_progress.place(**POS_TRACK_DURATION_PROGRESS)
                    # self.track_duration_total.place(**POS_TRACK_DURATION_TOTAL)
                elif h >= 200:
                    print(200)
                    self.control_panel_frame.place(**POS_CONTROL_PANEL_FRAME)
                    self.control_panel_frame.configure(width=w-26*2)
                    self.background.configure(width=w-26, height=(h - self.control_panel_frame.winfo_height()), fg_color=COLOR_SECOND_BACKGROUND)
                    
                    self.track_title.place_configure(x=labels_x, rely=0.5, y=-12, anchor="w")
                    self.track_artist.place_configure(x=labels_x, rely=0.5, y=8, anchor="w")
                    self.track_duration.place_forget()
                    
                    self.track_duration_slider.place(**POS_TRACK_DURATION_SLIDER)
                    self.track_duration_slider.configure(width=(self.control_panel_frame.winfo_width()-84))
                    # self.track_duration_progress.place(**POS_TRACK_DURATION_PROGRESS)
                    # self.track_duration_total.place(**POS_TRACK_DURATION_TOTAL)
                elif h < 80:
                    print(80)
                    self.track_title.place_configure(x=labels_x, rely=0.5, y=-10, anchor="w")
                    self.track_artist.place_configure(x=labels_x, rely=0.5, y=10, anchor="w")
                    
                    self.settings_button.place_forget()
                    self.track_duration.place_forget()
                    self.buttons_frame.place_forget()

                if self.current_image_url:
                    self.update_album_cover(self.current_image_url, cover_size)
                else:
                    self.update_album_cover(None, cover_size)
        
        except Exception as e:
            print(f"Error in adjust_layout: {e}")     
        finally:
            self._adjusting_layout = False

    def _on_resize_start(self, event):
        self._resizing = True
        self._resize_start_x = self.winfo_pointerx()
        self._resize_start_y = self.winfo_pointery()
        self._resize_start_w = self.winfo_width()
        self._resize_start_h = self.winfo_height()

    def _on_resizing(self, event):
        if not self._resizing:
            return
        # compute delta from start pointer
        dx = self.winfo_pointerx() - self._resize_start_x
        dy = self.winfo_pointery() - self._resize_start_y

        new_w = max(self.MIN_WIDTH, min(self.MAX_WIDTH, int(self._resize_start_w + dx)))
        new_h = max(self.MIN_HEIGHT, min(self.MAX_HEIGHT, int(self._resize_start_h + dy)))

        # set new geometry but keep current x,y (position)
        geo = self.geometry().split("+") # get current position
        if len(geo) >= 3: # geometry like "WxH+X+Y"
            pos_x = int(geo[1])
            pos_y = int(geo[2])
            self.geometry(f"{new_w}x{new_h}+{pos_x}+{pos_y}")
        else:
            self.geometry(f"{new_w}x{new_h}")

        self.after(50, self.adjust_layout)

    def _on_resize_end(self, event):
        self._resizing = False
        self.adjust_layout()

    def _on_configure(self, event):
        self.adjust_layout()
    
    def _get_cover_size(self):
        h = self.winfo_height()
        if h > 340:
            size = h - (10 + self.control_panel_frame.winfo_height() + 80)
        elif h > 200:
            size = h - (10 + self.control_panel_frame.winfo_height()) # size with control panel
        else:
            size = h - 10 # normal size
            
        return max(40, min(350, size)) # 350 - max cover size

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
    