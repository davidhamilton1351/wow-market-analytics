import gzip
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

# Settings: the only lines to change for another realm or game version
REGION = "us"
NAMESPACE = f"dynamic-classic-{REGION}"
CONNECTED_REALM_ID = 4385
CONTAINER = "raw"

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

# 2. Download every auction listing
auctions_response = requests.get(auctions_url, params=params, headers=headers)
auctions_response.raise_for_status()
data = auctions_response.json()
print(f"Downloaded {len(data.get('auctions', [])):,} auctions")

# 3. Compress the raw snapshot (JSON shrinks a lot)
now = datetime.now(timezone.utc)
compressed = gzip.compress(json.dumps(data).encode("utf-8"))
print(f"Compressed {len(auctions_response.content):,} bytes down to {len(compressed):,} bytes")

# 4. Build an organized path: one folder per game version, realm, and day
blob_path = (
    f"auctions/namespace={NAMESPACE}/realm={CONNECTED_REALM_ID}/"
    f"date={now:%Y-%m-%d}/snapshot_{now:%Y%m%dT%H%M%SZ}.json.gz"
)

# 5. Upload to Azure if we have a connection string, otherwise save locally
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
if connection_string:
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service.get_blob_client(container=CONTAINER, blob=blob_path)
    blob_client.upload_blob(compressed)
    print(f"Uploaded to Azure: {CONTAINER}/{blob_path}")
else:
    local_file = Path("data/raw") / blob_path
    local_file.parent.mkdir(parents=True, exist_ok=True)
    local_file.write_bytes(compressed)
    print(f"No Azure connection string found; saved locally to {local_file}")