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

# NOTE:
# this Client ID belongs to the original author of the project.
# if you are using this repository as a base for your own application,
# please create your own Spotify app on https://developer.spotify.com/dashboard and replace CLIENT_ID and REDIRECT_URI.

CLIENT_ID = "a1b19019bc5f4e0c916ad8b243f1e2f5" # Do NOT use this Client ID for production or redistributed builds.
REDIRECT_URI = "http://127.0.0.1:8888/callback"
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