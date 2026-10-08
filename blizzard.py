"""Shared helpers for calling Blizzard's API and saving data to Azure."""
import gzip
import json
import os
import time
from pathlib import Path

import requests
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()
session = requests.Session()  # reuses one connection for many requests, which is faster


def get_token():
    """Trade our client ID + secret for a temporary access token."""
    response = session.post(
        "https://oauth.battle.net/token",
        data={"grant_type": "client_credentials"},
        auth=(os.getenv("BLIZZARD_CLIENT_ID"), os.getenv("BLIZZARD_CLIENT_SECRET")),
    )
    response.raise_for_status()
    return response.json()["access_token"]


def api_get(path, namespace, token, region="us", retries=3):
    """GET an API path, retrying if Blizzard says 'slow down' or has a hiccup."""
    for attempt in range(retries):
        response = session.get(
            f"https://{region}.api.blizzard.com{path}",
            params={"namespace": namespace, "locale": "en_US"},
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt)  # wait 1s, then 2s, then 4s
            continue
        response.raise_for_status()
        return response.json()
    response.raise_for_status()


def save_gz_json(data, blob_path, container="raw"):
    """Compress data and upload it to Azure (or save locally if no Azure connection)."""
    compressed = gzip.compress(json.dumps(data).encode("utf-8"))
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string and os.getenv("GITHUB_ACTIONS") == "true":
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is missing in GitHub Actions.")
    if connection_string:
        blob = BlobServiceClient.from_connection_string(connection_string).get_blob_client(
            container=container, blob=blob_path)
        blob.upload_blob(compressed)
        print(f"Uploaded to Azure: {container}/{blob_path} ({len(compressed):,} bytes)")
    else:
        local_file = Path("data") / container / blob_path
        local_file.parent.mkdir(parents=True, exist_ok=True)
        local_file.write_bytes(compressed)
        print(f"Saved locally: {local_file}")