"""External search links; these do not assert a matched business identity."""
from urllib.parse import quote


def get_2gis_search_url(poi_name: str, city: str = "Астана") -> str:
    query = quote(f"{poi_name} {city}")
    return f"https://2gis.kz/astana/search/{query}"
