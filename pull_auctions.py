from datetime import datetime, timezone
from urllib.parse import urlparse

from blizzard import api_get, get_token, save_gz_json

# Settings: the only lines to change for another realm or game version
REGION = "us"
NAMESPACE = f"dynamic-classic-{REGION}"
CONNECTED_REALM_ID = 4385


def href_to_path(href):
    """Turn Blizzard's full link into a clean API path (no query string or trailing slash)."""
    return urlparse(href).path.rstrip("/")


token = get_token()
now = datetime.now(timezone.utc)
stamp = f"date={now:%Y-%m-%d}/snapshot_{now:%Y%m%dT%H%M%SZ}.json.gz"

# 1. Realm auctions (gear, bags, pets: non-stackable items)
realm = api_get(f"/data/wow/connected-realm/{CONNECTED_REALM_ID}", NAMESPACE, token)
data = api_get(href_to_path(realm["auctions"]["href"]), NAMESPACE, token)
print(f"Realm auctions: {len(data.get('auctions', [])):,} listings")
save_gz_json(data, f"auctions/namespace={NAMESPACE}/realm={CONNECTED_REALM_ID}/{stamp}")

# 2. Region-wide commodities (stackable items). Empty for MoP Classic as of Oct 2026;
#    we check every hour so we catch it automatically if Blizzard starts publishing it.
commodities_link = data.get("commodities", {}).get("href")
if commodities_link:
    commodities = api_get(href_to_path(commodities_link), NAMESPACE, token)
    listings = commodities.get("auctions", [])
    print(f"Commodities: {len(listings):,} listings")
    if listings:
        save_gz_json(commodities, f"commodities/namespace={NAMESPACE}/{stamp}")