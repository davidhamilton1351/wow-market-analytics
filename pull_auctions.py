import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# Settings: the only lines to change for another realm or game version
REGION = "us"
NAMESPACE = f"dynamic-classic-{REGION}"
CONNECTED_REALM_ID = 4385

# Get an access token
token_response = requests.post(
    "https://oauth.battle.net/token",
    data={"grant_type": "client_credentials"},
    auth=(os.getenv("BLIZZARD_CLIENT_ID"), os.getenv("BLIZZARD_CLIENT_SECRET")),
)
token_response.raise_for_status()
headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
params = {"namespace": NAMESPACE, "locale": "en_US"}

# 1. Ask Blizzard where this realm's auction data lives
realm_url = f"https://{REGION}.api.blizzard.com/data/wow/connected-realm/{CONNECTED_REALM_ID}"
realm_response = requests.get(realm_url, params=params, headers=headers)
realm_response.raise_for_status()
auctions_href = realm_response.json()["auctions"]["href"]
auctions_url = auctions_href.split("?")[0].rstrip("/")  # drop Blizzard's query string and trailing slash

# 2. Follow that link and download every auction listing
auctions_response = requests.get(auctions_url, params=params, headers=headers)
auctions_response.raise_for_status()
data = auctions_response.json()
auctions = data.get("auctions", [])
print(f"Downloaded {len(auctions)} auctions")

# 3. Save the raw snapshot with a timestamp in the filename
snapshot_time = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out_dir = Path("data/raw")
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / f"{NAMESPACE}_{CONNECTED_REALM_ID}_{snapshot_time}.json"
out_file.write_text(json.dumps(data))
print("Saved to", out_file)

# 4. Show one auction so we can see what the data looks like
if auctions:
    print(json.dumps(auctions[0], indent=2))