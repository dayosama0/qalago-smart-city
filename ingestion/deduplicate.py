"""Merge nearby OSM representations, preserving distinct chain branches."""
import json
import re
import unicodedata
from core.geo import haversine_m

_TRANSLIT = str.maketrans(dict(zip("абвгдеёзийклмнопрстуфхцэ", ["a","b","v","g","d","e","e","z","i","i","k","l","m","n","o","p","r","s","t","u","f","h","c","e"])))

def name_key(value):
    value = unicodedata.normalize("NFKC", value).casefold().replace("вэй", "way").replace("вей", "way").replace("й", "y").replace("ы", "y")
    return re.sub(r"[^a-z0-9]", "", value.translate(_TRANSLIT))

def deduplicate_records(records):
    kept = []
    removed = 0
    # Prefer records with field evidence and richer source data.
    for row in sorted(records, key=lambda r: (-len(r.get("verified_fields_json", "")), -len(r.get("tags_json", "")), r["id"])):
        tags = json.loads(row.get("tags_json") or "{}")
        names = {name_key(row["name"])} | {name_key(v) for k,v in tags.items() if k.startswith("name:") or k == "official_name"}
        duplicate = None
        for other, other_names in kept:
            if row["category"] != other["category"] or not names & other_names:
                continue
            # Buildings can have a node and polygon with distant centres.
            limit = 200 if row["category"] == "mall" else 60
            if haversine_m(row["lat"], row["lon"], other["lat"], other["lon"]) <= limit:
                duplicate = other
                break
        if duplicate is None:
            kept.append((row, names))
        else:
            removed += 1
            for field in ("description", "description_source", "opening_hours"):
                if not duplicate.get(field) and row.get(field):
                    duplicate[field] = row[field]
            evidence = json.loads(duplicate.get("verified_fields_json") or "{}")
            for field, source in json.loads(row.get("verified_fields_json") or "{}").items():
                if field not in evidence:
                    # Evidence can also describe coordinates or tag-derived facts.
                    if field in row:
                        duplicate[field] = row[field]
                    evidence[field] = source
            duplicate["verified_fields_json"] = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    return [row for row, _ in kept], removed
