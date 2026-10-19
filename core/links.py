"""External links; no network calls, route or matched-business guarantees.

Google Maps universal directions syntax:
https://developers.google.com/maps/documentation/urls/get-started#directions
"""
from urllib.parse import quote, urlencode

from core.geo import resolve_origin, validate_coordinates
from core.models import RecommendRequest


def get_2gis_search_url(poi_name: str, city: str = "Астана") -> str:
    query = quote(f"{poi_name} {city}")
    return f"https://2gis.kz/astana/search/{query}"


def get_walking_navigation_url(request: RecommendRequest, destination_latitude: float,
                               destination_longitude: float, *,
                               share_custom_origin: bool = False) -> str | None:
    """Link to Google Maps walking directions, never request a route here.

    Public preset origins can be shared. A manually supplied origin produces
    no URL unless the caller confirms explicit consent for this origin.
    Both points are coordinates, with no implied POI entrance/identity match.
    """
    if request.location_preset == "custom" and share_custom_origin is not True:
        return None
    latitude, longitude = resolve_origin(request)
    destination = validate_coordinates(destination_latitude, destination_longitude)
    params = {
        "api": "1",
        "origin": f"{latitude:.7f},{longitude:.7f}",
        "destination": f"{destination[0]:.7f},{destination[1]:.7f}",
        "travelmode": "walking",
    }
    return "https://www.google.com/maps/dir/?" + urlencode(params)
