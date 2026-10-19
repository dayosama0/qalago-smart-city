"""Explicit small-area fallback when public Overpass services are unavailable.

This uses four small public OSM API map requests, not the full Astana boxes.
The primary ingestion method remains Overpass. Never run from app startup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import requests

from ingestion.fetch_osm import utc_now
from ingestion.normalize import category_from_tags, retained_tags

ENDPOINT = "https://api.openstreetmap.org/api/0.6/map"
# west,south,east,north; public landmark areas, not user locations.
PRESET_BOXES = {
    "expo": (71.395, 51.081, 71.421, 51.100),
    "baiterek": (71.419, 51.120, 71.442, 51.138),
    "central_park": (71.404, 51.155, 71.430, 51.176),
    "airport": (71.451, 51.019, 71.484, 51.037),
}


def xml_to_elements(raw: bytes) -> list[dict]:
    """Use complete node geometry for approximate way bbox centers only."""
    root = ET.fromstring(raw)
    if root.tag != "osm":
        raise ValueError("Expected genuine OSM XML")
    nodes = {int(node.attrib["id"]): (float(node.attrib["lat"]), float(node.attrib["lon"]))
             for node in root.findall("node")}
    ways = {int(way.attrib["id"]): [int(node.attrib["ref"]) for node in way.findall("nd")]
            for way in root.findall("way")}
    result = []
    for element in root:
        if element.tag not in {"node", "way", "relation"}:
            continue
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in element.findall("tag")}
        if category_from_tags(tags) is None:
            continue
        record = {"type": element.tag, "id": int(element.attrib["id"]), "tags": retained_tags(tags)}
        if element.tag == "node":
            record.update(lat=float(element.attrib["lat"]), lon=float(element.attrib["lon"]))
        else:
            if element.tag == "way":
                refs = ways[int(element.attrib["id"])]
            else:
                # Complete multipolygon outer ways establish an approximate bbox
                # center; partial route/boundary relations never do.
                if tags.get("type") != "multipolygon":
                    continue
                outer_refs = [int(member.attrib["ref"]) for member in element.findall("member")
                              if member.attrib.get("type") == "way" and member.attrib.get("role") in {"outer", ""}]
                if not outer_refs or any(ref not in ways for ref in outer_refs):
                    continue
                refs = [ref for way in outer_refs for ref in ways[way]]
            if not refs or any(ref not in nodes for ref in refs):
                continue
            points = [nodes[ref] for ref in refs]
            record["center"] = {
                "lat": (min(p[0] for p in points) + max(p[0] for p in points)) / 2,
                "lon": (min(p[1] for p in points) + max(p[1] for p in points)) / 2,
            }
        result.append(record)
    return result


def collect(snapshots_dir: Path, raw_dir: Path, *, offline: bool = False) -> dict:
    raw_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    groups: dict[str, dict] = {"astana": {}, "airport": {}}
    sources: dict[str, list] = {"astana": [], "airport": []}
    previous_sources = {}
    if offline:
        for area in groups:
            metadata = json.loads((snapshots_dir / f"{area}.metadata.json").read_text(encoding="utf-8"))
            previous_sources.update({item["preset"]: item for item in metadata["requests"]})
    for preset, bbox in PRESET_BOXES.items():
        raw_path = raw_dir / f"{preset}.osm"
        if offline:
            raw = raw_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != previous_sources[preset]["original_xml_sha256"]:
                raise ValueError(f"Original XML hash mismatch for {preset}")
        else:
            response = requests.get(
                ENDPOINT, params={"bbox": ",".join(map(str, bbox))},
                headers={"User-Agent": "QalaGo-MVP/1.0 (four small public landmark snapshots)"},
                timeout=(10, 45),
            )
            response.raise_for_status()
            raw = response.content
            raw_path.write_bytes(raw)
        elements = xml_to_elements(raw)
        area = "airport" if preset == "airport" else "astana"
        for element in elements:
            groups[area][f"{element['type']}:{element['id']}"] = element
        sources[area].append({
            "preset": preset, "endpoint": ENDPOINT,
            "request_url": previous_sources[preset]["request_url"] if offline else response.url,
            "bbox_west_south_east_north": list(bbox),
            "fetched_at": previous_sources[preset]["fetched_at"] if offline else utc_now(),
            "original_xml_sha256": hashlib.sha256(raw).hexdigest(),
            "original_xml_bytes": len(raw), "category_elements": len(elements),
        })
    for area in groups:
        payload = {
            "version": 0.6,
            "generator": "QalaGo OSM API XML-to-JSON conversion; sanitized category subset",
            "copyright": "© OpenStreetMap contributors; ODbL 1.0",
            "elements": list(groups[area].values()),
        }
        path = snapshots_dir / f"{area}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        path.with_suffix(".metadata.json").write_text(json.dumps({
            "area": area, "source": "OpenStreetMap API 0.6 map (small-area fallback)",
            "fetched_at": max(item["fetched_at"] for item in sources[area]),
            "license": "ODbL 1.0", "derivation": "Selected original category tags; contacts and mapper metadata omitted. Node coordinates unchanged; way and complete multipolygon centers computed from complete outer bbox geometry. Incomplete relations omitted.",
            "coverage": "Four small landmark areas; NOT the full Overpass city/airport bounding boxes.",
            "requests": sources[area], "raw_elements": len(groups[area]),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {area: len(elements) for area, elements in groups.items()}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots-dir", type=Path, default=root / "data" / "snapshots")
    parser.add_argument("--raw-dir", type=Path, default=root / "data" / "raw")
    parser.add_argument("--offline", action="store_true", help="Reconvert hash-matched existing XML; preserve original fetch times")
    args = parser.parse_args()
    try:
        print(json.dumps(collect(args.snapshots_dir, args.raw_dir, offline=args.offline), indent=2))
    except (requests.RequestException, ValueError, OSError, ET.ParseError) as error:
        parser.exit(1, f"OSM API snapshot failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
