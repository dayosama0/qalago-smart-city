"""Order an existing result without retrieval or explanation calls."""
from core.models import Recommendation

SORT_OPTIONS = {
    "recommended": "По рекомендации",
    "distance": "Сначала ближайшие",
    "duration": "Меньше общего времени",
    "name": "По названию",
}


def sort_results(items: list[Recommendation], order: str) -> list[Recommendation]:
    if order not in SORT_OPTIONS:
        raise ValueError("Unknown result order")

    def key(item):
        closed = item.opening_status in {"closed", "closes_during_visit"}
        value = {"recommended": 0, "distance": item.distance_m,
                 "duration": item.total_minutes_estimated, "name": item.name.casefold()}[order]
        return closed, value

    # Stable sorting preserves recommendation order for equal values.
    return sorted(items, key=key)
