"""Two real calculations with a shared clock and weather observation."""
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path

from core.geo import resolve_origin
from core.models import RecommendRequest, RecommendResponse
from core.recommend import _request_time, recommend
from core.weather import get_weather


@dataclass
class ClimateComparison:
    off: RecommendResponse
    on: RecommendResponse
    explanation: str
    outdoor_difference_minutes: float | None
    evaluated_at: str


def _options(response: RecommendResponse):
    return [*response.recommendations, *response.alternatives]


def compare_climate_shield(request: RecommendRequest, db_path: str | Path | None = None) -> ClimateComparison:
    """Isolate Shield's effect. No second weather fetch or paid LLM generation.

    The original clock mode stays visible, even though both calculations share
    one captured instant. A missing first option has no comparable exposure;
    it must never be reported as a zero-minute improvement.
    """
    instant = _request_time(request)
    weather = get_weather(request.weather_mode, *resolve_origin(request))
    common = {"db_path": db_path, "evaluation_time": instant, "use_llm": False}
    off = recommend(replace(request, climate_shield_enabled=False),
                    weather_override=deepcopy(weather), **common)
    on = recommend(replace(request, climate_shield_enabled=True),
                   weather_override=deepcopy(weather), **common)
    off_options, on_options = _options(off), _options(on)
    difference = (round(off.estimated_outdoor_minutes - on.estimated_outdoor_minutes, 1)
                  if off_options and on_options else None)
    english = request.language.casefold().startswith("en")
    if not off_options and not on_options:
        explanation = ("Neither calculation found a valid option. No outdoor-time comparison is available."
                       if english else "Оба расчёта не нашли допустимых вариантов. Сравнить время на улице нельзя.")
    elif not on_options:
        explanation = ("Shield excluded all remaining options under the selected weather constraints. No improvement is claimed."
                       if english else "Shield исключил оставшиеся варианты по погодным ограничениям. Улучшение времени не заявляется.")
    elif not off_options:
        explanation = ("Only the Shield calculation has an option; there is no matching pair to compare."
                       if english else "Вариант найден только с Shield; пары для сравнения нет.")
    elif [p.poi_id for p in off_options] == [p.poi_id for p in on_options]:
        explanation = ("The selected places and order are unchanged. These data do not demonstrate a reduction in outdoor exposure."
                       if english else "Места и их порядок совпали. Эти данные не показывают сокращения времени на улице.")
    else:
        explanation = ("Shield applies weather constraints and indoor suitability before ranking; the results changed. Exposure is an estimate for each side's first option."
                       if english else "Shield применяет погодные ограничения и учитывает помещение перед ранжированием; результаты изменились. Время на улице — оценка первого варианта с каждой стороны.")
    if not on.recommendations and on.alternatives:
        explanation += (" No direct interest match remains with Shield; its places are alternatives in other categories."
                        if english else " С Shield прямых совпадений интересам нет; показаны альтернативы в других категориях.")
    return ClimateComparison(off, on, explanation, difference, instant.isoformat())
