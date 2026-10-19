import math

import pytest

from core.geo import haversine_m, resolve_origin, validate_coordinates, walking_minutes
from core.links import get_2gis_search_url
from core.models import RecommendRequest


def test_haversine_same_point_and_known_equatorial_degree():
    assert haversine_m(51.1, 71.4, 51.1, 71.4) == 0
    assert haversine_m(0, 0, 0, 1) == pytest.approx(111_195, abs=10)
    assert haversine_m(0, 0, 0, 1) == haversine_m(0, 1, 0, 0)


def test_walking_uses_documented_detour_and_speed():
    assert walking_minutes(1000) == pytest.approx(1.3 / 4.5 * 60)
    assert walking_minutes(0) == 0
    with pytest.raises(ValueError):
        walking_minutes(-1)


@pytest.mark.parametrize("lat,lon", [(91, 71), (51, 181), (math.nan, 71), (51, math.inf), (None, 71), (True, 71)])
def test_invalid_coordinates_rejected(lat, lon):
    with pytest.raises(ValueError):
        validate_coordinates(lat, lon)


def test_presets_and_custom_origins():
    assert haversine_m(*resolve_origin(RecommendRequest(location_preset="airport")), 51.028, 71.4635) < 300
    assert resolve_origin(RecommendRequest(location_preset="custom", latitude=51.1, longitude=71.4)) == (51.1, 71.4)
    with pytest.raises(ValueError):
        resolve_origin(RecommendRequest(location_preset="invalid"))


def test_2gis_search_is_encoded_and_only_a_search():
    from urllib.parse import unquote
    url = get_2gis_search_url("Кофе & парк")
    assert url.startswith("https://2gis.kz/astana/search/")
    assert "Кофе & парк Астана" in unquote(url)
    assert " " not in url
