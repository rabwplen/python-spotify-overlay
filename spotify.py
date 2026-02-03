import os
import sys
import threading
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

import spotipy
from spotipy.oauth2 import SpotifyPKCE

from utils import file_path, get_data_path

# Constants
CLIENT_ID = "PASTE_YOUR_CLIENT_ID"        # to get your client_id, create app in https://developer.spotify.com/dashboard
REDIRECT_URI = "http://127.0.0.1:8888/callback"  # or you can set your Redirect URI from your app
SCOPE = "user-read-private user-read-playback-state"

auth_code = None  # intermediate variable for storing code

# Authorization Handler
class AuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        if "/callback?" in self.path:
            code = self.path.split("code=")[-1].split("&")[0]
            auth_code = code

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            # Download HTML from a file
            html_path = Path(file_path("auth_success.html"))
            if html_path.exists():
                with open(html_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"<h1>Logged in</h1>")
                self.wfile.write(b"<h3>Error: HTML file not found</h3>")

# Server Functions
def run_server():
    server = HTTPServer(("localhost", 8888), AuthHandler)
    server.handle_request()

server_thread = threading.Thread(target=run_server, daemon=True)

# Authorization Setup
def setup_spotify():
    server_thread.start()

    cache_path = get_data_path(".cache")
    auth_manager = SpotifyPKCE(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=cache_path
    )

    token_info = auth_manager.get_cached_token()

    if not token_info:
        auth_url = auth_manager.get_authorize_url()
        webbrowser.open(auth_url)
        print("Waiting for authorization via browser...")

        server_thread.join() # waiting for the code (the server will receive it itself)

        code = auth_code
        token_info = auth_manager.get_access_token(code)

    sp = spotipy.Spotify(auth_manager=auth_manager)
    try:
        print("-< Authorized as:", sp.current_user()['display_name'], ">-")
    except:
        print("-< You are offline >-")
    
    return sp # return the sp object