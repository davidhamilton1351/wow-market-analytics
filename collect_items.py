from datetime import datetime, timezone

import requests

from blizzard import api_get, get_token, load_latest_gz_json, save_gz_json

REGION = "us"
ITEM_NAMESPACE = f"static-classic-{REGION}"  # Classic item data, so names match MoP Classic
AUCTION_PREFIX = f"auctions/namespace=dynamic-classic-{REGION}/realm=4385/"
RECIPE_PREFIX = f"recipes/namespace=static-{REGION}/"

# 1. Gather every item ID we care about. A "set" automatically ignores duplicates.
item_ids = set()

auctions = load_latest_gz_json(AUCTION_PREFIX)["auctions"]
item_ids.update(a["item"]["id"] for a in auctions)
print(f"{len(item_ids):,} unique items on the auction house")

for row in load_latest_gz_json(RECIPE_PREFIX)["recipes"]:
    recipe = row["recipe"]
    for key in ("crafted_item", "alliance_crafted_item", "horde_crafted_item"):
        if key in recipe:
            item_ids.add(recipe[key]["id"])
    for reagent in recipe.get("reagents", []):
        item_ids.add(reagent["reagent"]["id"])
print(f"{len(item_ids):,} unique items including recipe items")

# 2. Look each item up in the CLASSIC item API
token = get_token()
items, missing = [], []
for count, item_id in enumerate(sorted(item_ids), start=1):
    try:
        items.append(api_get(f"/data/wow/item/{item_id}", ITEM_NAMESPACE, token))
    except requests.HTTPError as error:
        if error.response.status_code == 404:
            missing.append(item_id)  # exists in retail but not in MoP Classic
        else:
            raise
    if count % 500 == 0:
        print(f"{count:,} / {len(item_ids):,} checked")

# 3. Save the results, including the list of missing items
now = datetime.now(timezone.utc)
save_gz_json(
    {"collected_at": now.isoformat(), "namespace": ITEM_NAMESPACE,
     "items": items, "missing_item_ids": missing},
    f"items/namespace={ITEM_NAMESPACE}/date={now:%Y-%m-%d}/items_{now:%Y%m%dT%H%M%SZ}.json.gz",
)
print(f"Done: {len(items):,} items found, {len(missing):,} not in MoP Classic")