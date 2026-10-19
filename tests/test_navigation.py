"""Navigation URL and private-origin boundary; no requests or route guarantees."""
from urllib.parse import parse_qs, urlparse

import pytest

from config import PRESETS
from core.links import get_walking_navigation_url
from core.models import RecommendRequest


def parameters(url):
    parsed = urlparse(url)
    assert parsed.scheme == "https" and parsed.netloc == "www.google.com"
    assert parsed.path == "/maps/dir/"
    return parse_qs(parsed.query)


@pytest.mark.parametrize("preset", list(PRESETS))
def test_public_preset_uses_selected_landmark_and_explicit_walking_mode(preset):
    # Stale manual fields must not replace the public landmark selected now.
    request = RecommendRequest(location_preset=preset, latitude=1.234567, longitude=2.345678)
    url = get_walking_navigation_url(request, 51.12828825, 71.4304546)
    params = parameters(url)
    assert params["api"] == ["1"] and params["travelmode"] == ["walking"]
    origin = tuple(map(float, params["origin"][0].split(",")))
    assert origin == pytest.approx((PRESETS[preset]["lat"], PRESETS[preset]["lon"]))
    assert tuple(map(float, params["destination"][0].split(","))) == pytest.approx((51.12828825, 71.4304546))
    assert "%2C" in url and "," not in url
    assert set(params) == {"api", "origin", "destination", "travelmode"}
    assert "1.234567" not in url


@pytest.mark.parametrize("consent", [False, None, 0, 1, "yes"])
def test_custom_origin_produces_no_url_without_explicit_boolean_consent(consent):
    request = RecommendRequest(location_preset="custom", latitude=51.1234567, longitude=71.1234567)
    assert get_walking_navigation_url(request, 51.1282, 71.4304, share_custom_origin=consent) is None


def test_custom_origin_is_included_only_after_explicit_consent():
    request = RecommendRequest(location_preset="custom", latitude=51.1234567, longitude=71.1234567)
    params = parameters(get_walking_navigation_url(request, 51.1282, 71.4304, share_custom_origin=True))
    assert params["origin"] == ["51.1234567,71.1234567"]
    assert params["destination"] == ["51.1282000,71.4304000"]
    assert params["travelmode"] == ["walking"]


@pytest.mark.parametrize("destination", [(float("nan"), 71.4), (51.1, float("inf")), (91, 71.4), (True, 71.4)])
def test_invalid_destination_cannot_become_an_external_link(destination):
    with pytest.raises(ValueError):
        get_walking_navigation_url(RecommendRequest(), *destination)


def test_invalid_consented_custom_origin_is_rejected():
    with pytest.raises(ValueError):
        get_walking_navigation_url(RecommendRequest(location_preset="custom", latitude=51.1, longitude=181),
                                   51.1282, 71.4304, share_custom_origin=True)
