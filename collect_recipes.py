from datetime import datetime, timezone

from blizzard import api_get, get_token, save_gz_json

REGION = "us"
NAMESPACE = f"static-{REGION}"  # retail static data (Classic has no profession API)
# Expansion tiers that exist in MoP Classic
TIER_KEYWORDS = ["Classic", "Outland", "Northrend", "Cataclysm", "Pandaria"]

token = get_token()
professions = api_get("/data/wow/profession/index", NAMESPACE, token)["professions"]

recipes = []
for prof in professions:
    detail = api_get(f"/data/wow/profession/{prof['id']}", NAMESPACE, token)
    for tier in detail.get("skill_tiers", []):  # some professions (e.g. Skinning) have no recipes
        if not any(word in tier["name"] for word in TIER_KEYWORDS):
            continue  # skip expansions after MoP
        tier_detail = api_get(f"/data/wow/profession/{prof['id']}/skill-tier/{tier['id']}", NAMESPACE, token)
        for category in tier_detail.get("categories", []):
            for r in category.get("recipes", []):
                recipe = api_get(f"/data/wow/recipe/{r['id']}", NAMESPACE, token)
                recipes.append({
                    "profession_id": prof["id"],
                    "profession_name": prof["name"],
                    "tier_id": tier["id"],
                    "tier_name": tier["name"],
                    "category_name": category["name"],
                    "recipe": recipe,  # the full, untouched API response
                })
        print(f"{tier['name']}: {len(recipes):,} recipes so far")

now = datetime.now(timezone.utc)
save_gz_json(
    {"collected_at": now.isoformat(), "namespace": NAMESPACE, "recipes": recipes},
    f"recipes/namespace={NAMESPACE}/date={now:%Y-%m-%d}/recipes_{now:%Y%m%dT%H%M%SZ}.json.gz",
)
print(f"Done: {len(recipes):,} recipes")