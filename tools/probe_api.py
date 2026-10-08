import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()
REGION = "us"
CLASSIC_BUILD_NS = f"static-5.5.4_67732-classic-{REGION}"  # from the item response; we'll detect this automatically later

token_response = requests.post(
    "https://oauth.battle.net/token",
    data={"grant_type": "client_credentials"},
    auth=(os.getenv("BLIZZARD_CLIENT_ID"), os.getenv("BLIZZARD_CLIENT_SECRET")),
)
token_response.raise_for_status()
headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

def get(path, namespace):
    return requests.get(f"https://{REGION}.api.blizzard.com{path}",
                        params={"namespace": namespace, "locale": "en_US"},
                        headers=headers)

# Test A: Classic professions using the build-specific namespace
r = get("/data/wow/profession/index", CLASSIC_BUILD_NS)
print(f"=== Classic profession list (build namespace): {r.status_code} ===")
if r.ok:
    print(json.dumps(r.json(), indent=2)[:600])

# Test B: Retail Blacksmithing -> list its expansion tiers
prof = get("/data/wow/profession/164", f"static-{REGION}").json()
print("\n=== Retail Blacksmithing tiers ===")
for tier in prof["skill_tiers"]:
    print(tier["id"], "-", tier["name"])

# Test C: Open the Pandaria tier and look at one full recipe
pandaria = next(t for t in prof["skill_tiers"] if "Pandaria" in t["name"])
tier = get(f"/data/wow/profession/164/skill-tier/{pandaria['id']}", f"static-{REGION}").json()
first = tier["categories"][0]["recipes"][0]
recipe = get(f"/data/wow/recipe/{first['id']}", f"static-{REGION}").json()
print(f"\n=== Sample Pandaria recipe: {first['name']} ===")
print(json.dumps(recipe, indent=2)[:1500])