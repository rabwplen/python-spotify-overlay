# Python Spotify Overlay

A simple, customizable overlay for Spotify that shows the currently playing track, artist, album art and playback controls on top of your screen.


## Features
- Real-time track info (title, artist, duration, cover)
- Play/Pause, Previous, Next buttons
- Adjustable opacity, fade effects
- Always-on-top, draggable, click-through mode
- Settings window & system tray menu
- Spotify login via browser


## Requirements
- Python 3.8+
- Libraries: `spotipy`, `customtkinter`, `pystray`, `pillow`, `requests`, `keyboard`

```bash
pip install spotipy customtkinter pystray pillow requests keyboard
```


## Installation
1. Clone or download the project
2. Install dependencies (see above)
3. Make sure the project structure looks like this:
    - assets/
    - main.py
    - overlay.py
    - settings.py
    - spotify.py
    - utils.py
4. Make sure the `assets/` folder contains:
    - `app-icon.ico` / `app-icon.png`
    - `close-icon.png`, `drag-icon.png`, `settings-icon.png`
    - `album-cover.jpeg` (default cover)


## Getting Started (Setup & Usage)

### 1. Spotify API Setup (Required)

This app uses the Spotify Web API, so you need your own **Client ID** and **Redirect URI**.

1. Go to https://developer.spotify.com/dashboard  
2. Log in → Create an app (any name/description is fine)  
3. In the app settings:
   - Copy your **Client ID**
   - Add Redirect URI: `http://127.0.0.1:8888/callback` (already used in the code)
4. Open `spotify.py` and replace the placeholders:

```python
CLIENT_ID = "PASTE_YOUR_CLIENT_ID"
REDIRECT_URI = "http://127.0.0.1:8888/callback"   # leave this as is
SCOPE = "user-read-private user-read-playback-state"
```

5. Save the file.


### 2. Run the App
```bash
python main.py
```

What happens on first launch:
1. The browser will open for Spotify authorization
2. The overlay appears → you can drag it, open settings, or use the tray icon
3. Tray menu: Hide/Show, Settings, Close

That’s it. After the first authorization, the app will reuse the cached token and won’t ask you again unless it expires.


## Settings
- Opacity (normal & hover)
- Fade delay & duration
- Always on top / Draggable / Click-through
- Changes are saved automatically


## Configuration Files
- settings.json: Stores user preferences (opacity, positions, etc.). Located in app data folder (e.g., %APPDATA%\rwp-PythonSpotifyOverlay on Windows).
- .cache: Spotify token cache (in the same folder).

Delete these files to reset to defaults.


## Troubleshooting
- No Song Info: Ensure Spotify is playing and you're online. Check console for API errors.
- Window Not Transparent/Draggable: Windows-specific (uses ctypes). On other OS, may need adjustments.
- Auth Fails: Check CLIENT_ID in spotify.py. Clear .cache file if issues.
- Freezing on drag: Fixed in recent versions using threaded updates (start_update_loop).
- Errors: Run in terminal for logs. Common: Missing libraries - reinstall deps.
If issues persist, check console output or open an issue on GitHub.

## Preview

![Overlay Preview](assets/preview.png)