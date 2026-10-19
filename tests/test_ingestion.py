"""Offline ETL tests; synthetic fixtures are never included in app snapshots."""

import json
from pathlib import Path
import sqlite3
from unittest.mock import Mock, patch

import pytest

from ingestion.build_database import apply_overrides, build_database, write_database
from ingestion.fetch_osm import DownloadError, build_query, download_area
from ingestion.fetch_osm_api import xml_to_elements
from ingestion.normalize import normalize_element, normalize_elements

FIXTURE = Path(__file__).parent / "fixtures" / "ingestion_test.json"
FETCHED = "2026-01-01T00:00:00Z"


def synthetic_records():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return normalize_elements(payload["elements"], FETCHED)[0]


def test_node_way_relation_and_validation():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    records, invalid, duplicate = normalize_elements(payload["elements"], FETCHED)
    assert {row["id"] for row in records} == {"osm:node:1", "osm:way:1", "osm:relation:2"}
    assert invalid == 4
    assert duplicate == 0
    assert records[1]["lat"] == 51.11
    assert records[2]["indoor_status"] == "confirmed_indoor"
    assert records[0]["power_outlets_status"] == "unknown"
    assert records[0]["opening_hours"] == "Mo-Fr 09:00-18:00"
    assert "phone" not in json.loads(records[0]["tags_json"])
    assert "opening_status" not in records[0]


@pytest.mark.parametrize("field,value", [("lat", float("nan")), ("lon", float("inf")), ("lat", True)])
def test_nonfinite_and_boolean_coordinates_rejected(field, value):
    element = {"type": "node", "id": 1, "lat": 51.1, "lon": 71.4,
               "tags": {"name": "SYNTHETIC", "amenity": "cafe"}}
    element[field] = value
    assert normalize_element(element, FETCHED) is None


def test_missing_name_not_replaced_by_invented_name():
    element = {"type": "node", "id": 1, "lat": 51.1, "lon": 71.4, "tags": {"amenity": "cafe"}}
    assert normalize_element(element, FETCHED) is None


def test_idempotent_rebuild_and_stable_type_ids(tmp_path):
    database = tmp_path / "synthetic.db"
    first = build_database([FIXTURE], database)
    second = build_database([FIXTURE], database)
    assert first["usable"] == second["usable"] == 3
    assert second["merged_replaced"] == 3
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM pois").fetchone()[0] == 3
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert len(connection.execute("SELECT id FROM pois WHERE id LIKE '%:1'").fetchall()) == 2


def test_rebuild_removes_absent_objects_and_preserves_existing_on_empty(tmp_path):
    database = tmp_path / "synthetic.db"
    records = synthetic_records()
    write_database(records, database)
    stats = write_database(records[:1], database)
    assert stats["removed_stale"] == 2
    with pytest.raises(ValueError, match="No usable"):
        write_database([], database)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM pois").fetchone()[0] == 1


def write_override(tmp_path, field="power_outlets_status", value="confirmed", poi_id="osm:node:1", evidence="https://example.org/synthetic-test-only"):
    path = tmp_path / "synthetic_overrides.csv"
    path.write_text("poi_id,field,value,evidence_url,checked_at\n"
                    f"{poi_id},{field},{value},{evidence},2026-01-01\n", encoding="utf-8")
    return path


def test_override_evidence_is_field_specific(tmp_path):
    records = synthetic_records()
    assert apply_overrides(records, write_override(tmp_path)) == 1
    provenance = json.loads(records[0]["verified_fields_json"])
    assert records[0]["power_outlets_status"] == "confirmed"
    assert set(provenance) == {"power_outlets_status"}
    assert provenance["power_outlets_status"]["evidence_url"] == "https://example.org/synthetic-test-only"
    assert records[0]["wifi_status"] == "confirmed"


@pytest.mark.parametrize("field,value,poi_id,evidence", [
    ("lat", "51.2", "osm:node:1", "https://example.org"),
    ("power_outlets_status", "maybe", "osm:node:1", "https://example.org"),
    ("visit_minutes", "0", "osm:node:1", "https://example.org"),
    ("indoor_status", "heated", "osm:node:1", "https://example.org"),
    ("wifi_status", "confirmed", "osm:node:999", "https://example.org"),
    ("wifi_status", "confirmed", "osm:node:1", "file:///private"),
])
def test_override_invalid_field_value_missing_id_or_evidence_rejected(tmp_path, field, value, poi_id, evidence):
    with pytest.raises(ValueError):
        apply_overrides(synthetic_records(), write_override(tmp_path, field, value, poi_id, evidence))


def test_build_query_is_numeric_bounded_and_contains_center():
    query = build_query((51.06, 71.31, 51.2, 71.54))
    assert "(51.060000,71.310000,51.200000,71.540000)" in query
    assert query.count("nwr[") == 5
    assert query.endswith("out center tags;\n")
    with pytest.raises(ValueError):
        build_query((51.2, 71.31, 51.06, 71.54))


def test_finite_retry_and_http_timeouts(tmp_path):
    response = Mock(status_code=429)
    session = Mock()
    session.post.return_value = response
    with patch("ingestion.fetch_osm.time.sleep") as sleep:
        with pytest.raises(DownloadError, match="after 2 attempts"):
            download_area("astana", tmp_path, attempts=2, session=session)
    assert session.post.call_count == 2
    assert session.post.call_args.kwargs["timeout"] == (10, 65)
    sleep.assert_called_once_with(2)
    assert not (tmp_path / "astana.json").exists()


def test_incomplete_overpass_download_is_never_cached(tmp_path):
    response = Mock(status_code=200)
    response.json.return_value = {"elements": [], "remark": "runtime timeout"}
    session = Mock()
    session.post.return_value = response
    with pytest.raises(DownloadError, match="incomplete response"):
        download_area("astana", tmp_path, attempts=1, session=session)
    assert not (tmp_path / "astana.json").exists()


def test_osm_api_conversion_omits_mapper_and_contact_metadata():
    xml = b'''<osm version="0.6"><node id="1" lat="51.1" lon="71.4" user="SYNTHETIC_USER" uid="99"><tag k="name" v="SYNTHETIC cafe"/><tag k="amenity" v="cafe"/><tag k="contact:phone" v="SYNTHETIC_PHONE"/></node><node id="2" lat="51.2" lon="71.5"/><way id="3"><nd ref="1"/><nd ref="2"/><tag k="name" v="SYNTHETIC park"/><tag k="leisure" v="park"/></way><way id="4"><nd ref="999"/><tag k="leisure" v="park"/></way></osm>'''
    elements = xml_to_elements(xml)
    assert len(elements) == 2
    assert elements[1]["center"] == {"lat": pytest.approx(51.15), "lon": pytest.approx(71.45)}
    serialized = json.dumps(elements)
    assert "SYNTHETIC_USER" not in serialized
    assert "SYNTHETIC_PHONE" not in serialized


def test_complete_multipolygon_center_and_incomplete_relation_policy():
    xml = b'''<osm version="0.6"><node id="1" lat="51.1" lon="71.4"/><node id="2" lat="51.2" lon="71.5"/><way id="3"><nd ref="1"/><nd ref="2"/></way><relation id="4"><member type="way" ref="3" role="outer"/><tag k="type" v="multipolygon"/><tag k="leisure" v="park"/><tag k="name" v="SYNTHETIC complete relation"/></relation><relation id="5"><member type="way" ref="999" role="outer"/><tag k="type" v="multipolygon"/><tag k="leisure" v="park"/><tag k="name" v="SYNTHETIC incomplete relation"/></relation></osm>'''
    elements = xml_to_elements(xml)
    assert len(elements) == 1
    assert elements[0]["type"] == "relation"
    assert elements[0]["id"] == 4
    assert elements[0]["center"]["lat"] == pytest.approx(51.15)


def test_historic_monument_is_source_backed_attraction():
    element = {"type": "way", "id": 10, "center": {"lat": 51.1, "lon": 71.4},
               "tags": {"name": "SYNTHETIC monument", "historic": "monument"}}
    record = normalize_element(element, FETCHED)
    assert record["category"] == "attraction"
    assert record["indoor_status"] == "unknown"
