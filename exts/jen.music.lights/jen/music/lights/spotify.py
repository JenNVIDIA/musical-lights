import asyncio
import base64
import random
import string
import webbrowser
from .constants import *
import aiohttp
import carb
import omni.kit.app
import omni.kit.commands
from pxr import Sdf
from aiohttp import web


# Constants for Spotify API
SPOTIFY_API = "https://api.spotify.com/v1/"
SPOTIFY_PLAY_URL = SPOTIFY_API + "me/player/play"
SPOTIFY_TRACK_ANAL_URL = SPOTIFY_API + "audio-analysis/"
DEFAULT_TRACK = "2BFGRjoK2ZXUa4JlMc3H7J"
SCOPE = 'user-read-playback-position user-read-currently-playing user-modify-playback-state'
AUTH_URL = "https://accounts.spotify.com/authorize?"
AUTH_HEADER_ALT = "response_type=" + "code" + "&client_id=" + CLIENTID + "&scope=" + SCOPE + "&redirect_uri=" + "http://localhost:8888/callback" + "&state=" + ''.join(random.choices(string.ascii_lowercase, k=16))

def startup_spotify_sync(track, auth_token):
    header = {
        "Authorization": f"Bearer {auth_token}"
    }
    run_loop = asyncio.get_event_loop()
    run_loop.run_until_complete(spotify_loop(track, header))

# Run Spotify connection
async def spotify_loop(track, header):
    is_playing = await store_data(track, header)
    if is_playing:
        asyncio.create_task(ov_play())

# Retrieve track analysis from spotify's API to then store it into the USD scene
async def store_data(track, headers):
    async with aiohttp.ClientSession() as session:
        data = await get_track_analysis(session, headers)
        if not data[0]:
            return
        else:
            start_times = []
            pitches = [[], [], [], [], [], [], [], [], [], [], [], []]
            segments = data[1]
            index = 0
            
            while index < len(segments):
                time = float(segments[index]['start'])
                start_times.append(time)
                # Store each pitch value at the specific start time value
                for i in range(12):
                    val = float(segments[index]['pitches'][i])
                    pitches[i].append(val)
                index += 1

            await generate_properties(start_times, data[2], pitches)

        is_playing = await play_song(session, track, headers)
        return is_playing

# Generate the properties that hold track analysis data
async def generate_properties(start_times, duration, pitches):
    # Store Information within the USD as Attributes
    create_attributes(Sdf.Path('/World.beat_start_time'), Sdf.ValueTypeNames.FloatArray)
    create_attributes(Sdf.Path('/World.duration'), Sdf.ValueTypeNames.Float)
    change_properties(Sdf.Path('/World.beat_start_time'), start_times)
    change_properties(Sdf.Path('/World.duration'), duration)
    
    # Create attribute for every pitch
    for i in range(12):
        create_attributes(Sdf.Path('/World.pitch' + str(i)), Sdf.ValueTypeNames.FloatArray)
        change_properties(Sdf.Path('/World.pitch' + str(i)), pitches[i])

# Uses Kit commands to change properties given the path and new value
def change_properties(path, new_value):
    omni.kit.commands.execute('ChangeProperty',
        prop_path=path,
        value=new_value,
        prev=None)

# Uses Kit commands to create an attribute given the path and attribute type
def create_attributes(path, attr_type):
    omni.kit.commands.execute('CreateUsdAttributeOnPath',
        attr_path=path,
        attr_type=attr_type,
        custom=True,
        variability=Sdf.VariabilityVarying)
 
# Get Information from the track analysis and grab specific pieces from the json
async def get_track_analysis(session, headers):
    async with session.get(SPOTIFY_TRACK_ANAL_URL + DEFAULT_TRACK, headers=headers) as resp:
        if resp.status == 200:
            json = await resp.json()
            segments = json["segments"]
            track = json["track"]
            duration = track["duration"]
            return [True, segments, duration]
        return [False, None, None]

# Plays the song on spotify if we recieve a OK response
async def play_song(session, track, headers):
    track_to_play = track
    if track == "":
        track_to_play = DEFAULT_TRACK
    async with session.put(SPOTIFY_PLAY_URL, json={"uris": ["spotify:track:" + track_to_play]},headers=headers) as play_resp:
        if play_resp.status == 204:
           return True
        else:
            return False

# Wait a little bit then run kit command for hitting Play
async def ov_play():
    await asyncio.sleep(0.1)
    omni.kit.commands.execute('ToolbarPlayButtonClicked')

# Web Authentication holder
class WebData:
    def __init__(self) -> None:
        self._access_code = ""
        self._auth_token = ""
        
    def get_access_code(self):
        self.run_web_app()
        run_loop = asyncio.get_event_loop()
        return run_loop.run_until_complete(self.boot_server())

    def get_access_token(self):
        run_loop = asyncio.get_event_loop()
        return run_loop.run_until_complete(self.auth_token_loop(self._access_code))

    def run_web_app(self):
        self.app = web.Application()
        self.app.add_routes([web.get('/callback', self.query_code)])

    async def boot_server(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8888)
        await site.start()

        while True:
            self.open_web_browser()
            await asyncio.sleep(5)
            await site.stop()
            break

    def open_web_browser(self):
        webbrowser.open(str(AUTH_URL+AUTH_HEADER_ALT))

    async def query_code(self, request):
        self._access_code = request.rel_url.query.get('code', '')
        return web.Response(text=f"You can close this now")

    async def auth_token_loop(self, code):
        authUrl = "https://accounts.spotify.com/api/token"
        form = aiohttp.FormData({
            "code": str(code),
            "redirect_uri": REDIRECT_URI,
            "grant_type": 'authorization_code'
        })
        client_string = CLIENTID + ':' + CLIENT_SECRET
        ascii_client = client_string.encode("ascii")
        base64_client = base64.b64encode(ascii_client)
        decode_client = base64_client.decode("ascii")
        headers = {
            'Authorization': f"Basic {decode_client}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method='POST', url=authUrl, headers=headers, data=form) as resp:
                if resp.status == 200:
                    json = await resp.json()
                    carb.log_info(f"json: {json}")
                    self._auth_token = json["access_token"]
                    carb.log_info(f"token: {self._auth_token}")
                else:
                    carb.log_info(f"Response Status: {resp.status}")
                    
