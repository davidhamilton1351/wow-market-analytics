import os
import requests
from dotenv import load_dotenv

load_dotenv()
REGION = "us"
NAMESPACE = f"dynamic-classic-{REGION}"

# Get an access token (same as before)
token_response = requests.post(
    "https://oauth.battle.net/token",
    data={"grant_type": "client_credentials"},
    auth=(os.getenv("BLIZZARD_CLIENT_ID"), os.getenv("BLIZZARD_CLIENT_SECRET")),
)
token_response.raise_for_status()
headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

# Get the list of connected realms
index = requests.get(
    f"https://{REGION}.api.blizzard.com/data/wow/connected-realm/index",
    params={"namespace": NAMESPACE, "locale": "en_US"},
    headers=headers,
)
index.raise_for_status()

# Visit each connected realm and print its ID and realm names
for entry in index.json()["connected_realms"]:
    detail = requests.get(entry["href"], params={"locale": "en_US"}, headers=headers)
    detail.raise_for_status()
    data = detail.json()
    names = ", ".join(realm["name"] for realm in data["realms"])
    print(data["id"], "-", names)