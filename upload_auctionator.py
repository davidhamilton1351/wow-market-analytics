"""Upload Auctionator's saved price database to Azure.

How to use (after an in-game Auctionator full scan + /reload):
    python upload_auctionator.py
The file location comes from AUCTIONATOR_FILE in your .env, or pass it directly:
    python upload_auctionator.py "C:\\...\\SavedVariables\\Auctionator.lua"

What's inside the file: Auctionator stores each realm's prices as one long
string of CBOR (a compact binary format, like a binary JSON). For each item:
    m = current minimum price (copper)
    a = {day: quantity available}   l = {day: low price}   h = {day: high price}
Days are counted from 2020-01-01 (day 2472 = 2026-10-08).
"""
import os
import re
import struct
import sys
from datetime import datetime, timezone

from blizzard import save_gz_json, blob_exists

REGION = "us"
NAMESPACE = f"dynamic-classic-{REGION}"
CONNECTED_REALM_ID = 4385  # Auctionator names the realm itself; we tag it with our realm ID


# ---------------------------------------------------------------------------
# Step 1: read Lua strings out of the file (undoing Lua's escape codes)
# ---------------------------------------------------------------------------
ESCAPES = {ord("n"): b"\n", ord("r"): b"\r", ord("t"): b"\t", ord("\\"): b"\\",
           ord('"'): b'"', ord("'"): b"'", ord("\n"): b"\n", ord("a"): b"\a",
           ord("b"): b"\b", ord("f"): b"\f", ord("v"): b"\v"}


def read_lua_string(raw, start):
    """raw[start] is an opening quote. Return (string bytes, index after closing quote)."""
    out = bytearray()
    i = start + 1
    while True:
        c = raw[i]
        if c == ord('"'):
            return bytes(out), i + 1
        if c == ord("\\"):
            nxt = raw[i + 1]
            if 48 <= nxt <= 57:  # \ddd = a byte written as up to 3 decimal digits
                j = i + 1
                while j < i + 4 and 48 <= raw[j] <= 57:
                    j += 1
                out.append(int(raw[i + 1:j]))
                i = j
                continue
            out += ESCAPES[nxt]
            i += 2
            continue
        out.append(c)
        i += 1


def find_price_database(raw):
    """Return {realm_name: cbor_bytes} from the AUCTIONATOR_PRICE_DATABASE table."""
    pos = raw.index(b"AUCTIONATOR_PRICE_DATABASE = {")
    entry = re.compile(rb'\s*\["([^"]+)"\] = ')
    pos = raw.index(b"{", pos) + 1
    realms = {}
    # Walk the table entry by entry, so binary data inside one string is never
    # mistaken for the start of the next entry
    while (match := entry.match(raw, pos)):
        name = match.group(1).decode("utf-8")
        pos = match.end()
        if raw[pos] == ord('"'):
            realms[name], pos = read_lua_string(raw, pos)
        else:  # a number, like ["__dbversion"] = 8
            pos = raw.index(b",", pos)
        pos += 1  # skip the comma
    return realms


def scan_time(raw):
    match = re.search(rb'\["TimeOfLastBrowseScan"\] = (\d+)', raw)
    return datetime.fromtimestamp(int(match.group(1)), timezone.utc) if match else None


# ---------------------------------------------------------------------------
# Step 2: decode CBOR (a small decoder, so there's no extra package to install)
# ---------------------------------------------------------------------------
def decode_cbor(data):
    value, pos = _cbor_item(data, 0)
    if pos != len(data):
        raise ValueError(f"CBOR decoded {pos} of {len(data)} bytes; the file may be damaged")
    return value


def _cbor_length(data, pos, info):
    if info < 24:
        return info, pos
    size = {24: 1, 25: 2, 26: 4, 27: 8}.get(info)
    if size is None:
        return None, pos  # 31 = "indefinite length"
    return int.from_bytes(data[pos:pos + size], "big"), pos + size


def _cbor_item(data, pos):
    first = data[pos]
    major, info = first >> 5, first & 0x1F
    pos += 1
    if major == 7:  # floats, true/false/null
        if info == 20: return False, pos
        if info == 21: return True, pos
        if info in (22, 23): return None, pos
        if info == 25: return struct.unpack(">e", data[pos:pos + 2])[0], pos + 2
        if info == 26: return struct.unpack(">f", data[pos:pos + 4])[0], pos + 4
        if info == 27: return struct.unpack(">d", data[pos:pos + 8])[0], pos + 8
        raise ValueError(f"Unsupported CBOR simple value {info} at byte {pos}")
    length, pos = _cbor_length(data, pos, info)
    if major == 0:
        return length, pos
    if major == 1:
        return -1 - length, pos
    if major in (2, 3):  # byte string / text string
        if length is None:
            raise ValueError("Indefinite-length strings are not supported")
        chunk = data[pos:pos + length]
        return chunk.decode("utf-8", errors="replace"), pos + length
    if major == 4:  # array
        items = []
        while (length is None and data[pos] != 0xFF) or (length is not None and len(items) < length):
            item, pos = _cbor_item(data, pos)
            items.append(item)
        return items, pos + (1 if length is None else 0)
    if major == 5:  # map
        result, count = {}, 0
        while (length is None and data[pos] != 0xFF) or (length is not None and count < length):
            key, pos = _cbor_item(data, pos)
            result[str(key)], pos = _cbor_item(data, pos)
            count += 1
        return result, pos + (1 if length is None else 0)
    if major == 6:  # tag: skip the tag number, keep the value
        return _cbor_item(data, pos)
    raise ValueError(f"Unknown CBOR type {major}")


# ---------------------------------------------------------------------------
# Step 3: run it
# ---------------------------------------------------------------------------
# When run with --log (by Task Scheduler), write output to a log file instead of the screen
if "--log" in sys.argv:
    sys.argv.remove("--log")
    from pathlib import Path
    Path("logs").mkdir(exist_ok=True)
    sys.stdout = sys.stderr = open("logs/auctionator_upload.log", "a", encoding="utf-8")
    print(f"\n--- {datetime.now():%Y-%m-%d %H:%M:%S} ---")
path = sys.argv[1] if len(sys.argv) > 1 else os.getenv("AUCTIONATOR_FILE")
if not path:
    sys.exit("Give the path to Auctionator.lua, or set AUCTIONATOR_FILE in .env")

raw = open(path, "rb").read()
scanned_at = scan_time(raw) or datetime.now(timezone.utc)
print(f"Last full scan: {scanned_at:%Y-%m-%d %H:%M} UTC")

for realm_name, cbor_bytes in find_price_database(raw).items():
    items = decode_cbor(cbor_bytes)
    with_price = sum(1 for v in items.values() if isinstance(v, dict) and "m" in v)
    print(f"{realm_name}: {len(items):,} items ({with_price:,} with a current price)")

    blob_path = (f"auctionator/namespace={NAMESPACE}/realm={CONNECTED_REALM_ID}/"
                 f"date={scanned_at:%Y-%m-%d}/scan_{scanned_at:%Y%m%dT%H%M%SZ}.json.gz")
    if blob_exists(blob_path):
        print(f"Already uploaded this scan ({blob_path}); skipping")
        continue
    save_gz_json({"source": "auctionator", "realm_key": realm_name,
                  "scanned_at": scanned_at.isoformat(), "items": items}, blob_path)