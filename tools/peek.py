import gzip
import json
import sys

# Open the compressed file, decompress it, and read the JSON
with gzip.open(sys.argv[1], "rt", encoding="utf-8") as f:
    data = json.load(f)

auctions = data["auctions"]
print(f"{len(auctions):,} auctions in this file")
print(json.dumps(auctions[0], indent=2))