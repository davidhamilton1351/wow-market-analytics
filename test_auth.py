import os
import requests
from dotenv import load_dotenv

# Read your credentials from the .env file
load_dotenv()
CLIENT_ID = os.getenv("BLIZZARD_CLIENT_ID")
CLIENT_SECRET = os.getenv("BLIZZARD_CLIENT_SECRET")
print("ID loaded:", bool(CLIENT_ID), "| Secret loaded:", bool(CLIENT_SECRET))

# Version-agnostic settings: change these, not the code below
REGION = "us"
NAMESPACE = f"dynamic-classic-{REGION}"

# Step 1: trade your ID + secret for a temporary access token
token_response = requests.post(
    "https://oauth.battle.net/token",
    data={"grant_type": "client_credentials"},
    auth=(CLIENT_ID, CLIENT_SECRET),
)
token_response.raise_for_status()  # stop with an error if this failed
token = token_response.json()["access_token"]
print("Got an access token!")

# Step 2: use the token to ask for the list of realms
realm_response = requests.get(
    f"https://{REGION}.api.blizzard.com/data/wow/connected-realm/index",
    params={"namespace": NAMESPACE, "locale": "en_US"},
    headers={"Authorization": f"Bearer {token}"},
)
realm_response.raise_for_status()
realms = realm_response.json()["connected_realms"]
print(f"Found {len(realms)} connected realms in {NAMESPACE}")