import os
import requests
from dotenv import load_dotenv

load_dotenv()
REGION = "us"
NAMESPACE = f"dynamic-classic-{REGION}"
CONNECTED_REALM_ID = 4385

token_response = requests.post(
    "https://oauth.battle.net/token",
    data={"grant_type": "client_credentials"},
    auth=(os.getenv("BLIZZARD_CLIENT_ID"), os.getenv("BLIZZARD_CLIENT_SECRET")),
)
token_response.raise_for_status()
headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
params = {"namespace": NAMESPACE, "locale": "en_US"}

realm_url = f"https://{REGION}.api.blizzard.com/data/wow/connected-realm/{CONNECTED_REALM_ID}"

# What does Blizzard say about this realm, and where does it say the auctions live?
detail = requests.get(realm_url, params=params, headers=headers)
print("Connected realm:", detail.status_code)
print("Auctions link Blizzard gives:", detail.json().get("auctions"))

# Try the possible auction addresses and report what each returns
for path in ["/auctions/index", "/auctions", "/auctions/2", "/auctions/6", "/auctions/7"]:
    response = requests.get(realm_url + path, params=params, headers=headers)
    print(f"{path:18} -> {response.status_code}")