import sys
import json
from datetime import datetime
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
from zoom_api import new_client

with open("zoom_secrets.json", "rb") as f:
    env = json.load(f)
    client_id = env["client_id"]
    client_secret = env["client_secret"]
    redirect_url = env["redirect_url"]

authorization_url = "https://zoom.us/oauth/authorize"
token_url = "https://zoom.us/oauth/token"
refresh_url = "https://zoom.us/oauth/token"
api_base = "https://api.zoom.us/v2"

class TokenDb:
    def __init__(self, fname, token):
        self._fname = fname
        self.token = token

    @classmethod
    def from_file(cls, fname):
        with open(fname) as f:
            token = json.load(f)
        return cls(fname, token)

    def needs_refresh(self):
        if "time" not in self.token:
            return True
        # refresh in half the expires_in time just to be safe
        # (Zoom always sets this to an hour, so we refresh every 30min)
        expiry_time = self.token["time"] + self.token["expires_in"] / 2
        now_unix = datetime.now().timestamp()
        if now_unix > expiry_time:
            return True
        return False

    def save(self):
        with open(self._fname, "w") as f:
            json.dump(self.token, f)

    def update(self, token):
        token["time"] = datetime.now().timestamp()
        self.token = token
        self.save()

db = TokenDb.from_file("token_secrets.json")

client = OAuth2Session(
        client_id,
        token=db.token,
        auto_refresh_url=refresh_url,
        token_updater=db.update,
)
if db.needs_refresh():
    auth = HTTPBasicAuth(client_id, client_secret)
    r = client.post(
        refresh_url,
        {"grant_type": "refresh_token", "refresh_token": db.token["refresh_token"]},
        auth=auth,
    )
    if r.status_code == 200:
        token = r.json()
        db.update(token)
    else:
        print("could not refresh", file=sys.stderr)
        print(r, file=sys.stderr)
        print(r.text, file=sys.stderr)
        sys.exit(1)

    client = OAuth2Session(client_id, token=db.token)

api_rooms = []
#api_rooms.append({"name": "hallway", "participants": []})
api_rooms.append({"name": "hallway", "participants": ["rsudarsanan210725@gmail.com", "ghobadi@mit.edu", "mahesh@gmail.com"]})

client = new_client()
r = client.patch(
    api_base + "/meetings/" + "4434429943",
    json={
        "settings": {
            "breakout_room": {
                "enable": True,
                "rooms": api_rooms,
            }
        }
    },
)
print("result:", r.text)