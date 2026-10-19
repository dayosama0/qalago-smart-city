"""Unified UI/backend entry point for deterministic structured RAG."""
from datetime import datetime
import math
from pathlib import Path

from config import TIMEZONE
from core.geo import resolve_origin
from core.llm import generate_explanations
from core.models import RecommendRequest, RecommendResponse, Recommendation, Weather
from core.ranking import estimated_outdoor_minutes, rank_candidates
from core.retrieval import DatabaseUnavailable, INTENT_CATEGORIES, get_candidates, has_flight_deadline, is_direct_match, parse_intents
from core.weather import get_weather


def _request_time(request: RecommendRequest) -> datetime:
    if request.time_mode == "live":
        return datetime.now(TIMEZONE)
    if request.time_mode != "simulated" or not request.simulated_datetime:
        raise ValueError("Simulated time requires a valid ISO datetime")
    try:
        value = datetime.fromisoformat(request.simulated_datetime)
    except (TypeError, ValueError) as exc:
        raise ValueError("Simulated time requires a valid ISO datetime") from exc
    return value.replace(tzinfo=TIMEZONE) if value.tzinfo is None else value.astimezone(TIMEZONE)


def _validate_request(request: RecommendRequest) -> None:
    if isinstance(request.duration_minutes, bool) or not isinstance(request.duration_minutes, int) or not 1 <= request.duration_minutes <= 480:
        raise ValueError("Duration must be an integer between 1 and 480 minutes")
    if not isinstance(request.query, str) or len(request.query) > 4000:
        raise ValueError("Query must be text of at most 4000 characters")
    if not isinstance(request.interests, list) or any(not isinstance(value, str) for value in request.interests):
        raise ValueError("Interests must be a list of strings")
    if request.weather_mode not in {"live", "clear", "wind", "rain", "cold"}:
        raise ValueError("Unknown weather mode")
    if request.time_mode not in {"live", "simulated"}:
        raise ValueError("Unknown time mode")
    for flag in (request.walking_only, request.return_to_start, request.climate_shield_enabled, request.flight_constraint):
        if not isinstance(flag, bool):
            raise ValueError("Request flags must be booleans")


def _opening_note(candidate, english: bool) -> str:
    freshness = candidate.opening_hours_checked_at or candidate.fetched_at or ("unknown" if english else "неизвестно")
    hours_source = candidate.opening_hours_source_url or candidate.source_url or candidate.source
    if candidate.opening_hours:
        if candidate.opening_status == "listed_open":
            status_note = ("According to the listed schedule, the selected time and estimated arrival/visit fit its hours. " if english else "Согласно указанному расписанию, выбранное время и расчётное посещение укладываются в часы работы. ")
        else:
            status_note = ("The full schedule could not be reliably interpreted; availability is unknown. " if english else "Полное расписание не удалось надёжно разобрать; доступность неизвестна. ")
        if english:
            return f"{status_note}Listed hours: {candidate.opening_hours}. Current availability not verified. Schedule source: {hours_source}; evidence/fetch date: {freshness}."
        return f"{status_note}Указанное расписание: {candidate.opening_hours}. Доступность сейчас не проверена. Источник расписания: {hours_source}; дата сведений/загрузки: {freshness}."
    if english:
        return f"Opening hours unknown; current availability not verified. Source: {candidate.source}; fetched {freshness}."
    return f"Часы работы неизвестны; доступность сейчас не проверена. Источник: {candidate.source}; загружено {freshness}."


def _template(candidate, intents, weather, english: bool) -> tuple[str, str, list[str]]:
    reasons = []
    warnings = []
    category_intents = [intent for intent in intents if intent in INTENT_CATEGORIES]
    if category_intents and not any(candidate.category in INTENT_CATEGORIES[intent] for intent in category_intents):
        reasons.append("An alternative in another category within the available constraints." if english else "Альтернатива в другой категории в пределах выбранных ограничений.")
        warnings.append("The category does not match the requested interests; this is an alternative." if english else "Категория не совпадает с выбранными интересами; это альтернативный вариант.")
    elif category_intents:
        reasons.append("The category is a possible match for your interests." if english else "Категория места может соответствовать вашим интересам.")
    else:
        reasons.append("A nearby option within the estimated time budget." if english else "Вариант рядом, укладывающийся в расчётный запас времени.")
    if "power_outlets" in intents:
        reasons.append("Power outlets are recorded as confirmed in the dataset." if english else "Розетки отмечены в базе как подтверждённые источником.")
    if "wifi" in intents:
        reasons.append("Wi-Fi is recorded as confirmed in the dataset." if english else "Wi-Fi отмечен в базе как подтверждённый источником.")
    if "accessibility" in intents:
        reasons.append("The source has wheelchair=yes; individual needs and route access still require checking." if english else "В источнике указано wheelchair=yes; индивидуальные условия и доступ по пути нужно уточнить.")
    if candidate.indoor_status == "likely_indoor":
        warnings.append("Likely indoors based on source tags/category; heating and shelter are not verified." if english else "Вероятно в помещении по тегам или категории; отопление и защищённость от погоды не проверены.")
    elif candidate.indoor_status == "unknown":
        warnings.append("Indoor/outdoor status is unknown." if english else "Неизвестно, находится ли место в помещении.")
    if weather.status in {"caution", "severe"}:
        warnings.append("Adverse weather: check current conditions; outdoor access is still required." if english else "Неблагоприятная погода: проверьте текущие условия; путь к месту проходит снаружи.")
    elif weather.status == "unknown":
        warnings.append("Weather is unknown; check conditions before leaving." if english else "Погода неизвестна; проверьте условия перед выходом.")
    if candidate.tags.get("type") in {"multipolygon", "route"} or candidate.id.startswith(("osm:way:", "osm:relation:")):
        warnings.append("Map position may be an approximate object centre, not an entrance." if english else "Точка на карте может быть центром объекта, а не входом.")
    actions = {
        "museum": ("Consider looking at the exhibits if access is available.", "Рассмотрите посещение экспозиции, если вход доступен."),
        "gallery": ("Consider viewing the exhibition if access is available.", "Рассмотрите осмотр экспозиции, если вход доступен."),
        "cafe": ("Consider a short stop; check the venue details first.", "Рассмотрите короткую остановку; заранее уточните условия посещения."),
        "restaurant": ("Consider a short stop; check the venue details first.", "Рассмотрите короткую остановку; заранее уточните условия посещения."),
        "park": ("Consider a short walk after checking the weather and access.", "Рассмотрите короткую прогулку после проверки погоды и доступа."),
        "garden": ("Consider a short walk after checking the weather and access.", "Рассмотрите короткую прогулку после проверки погоды и доступа."),
        "playground": ("Inspect the area and decide whether a short stop suits your group.", "Осмотритесь и оцените, подходит ли короткая остановка вашей компании."),
    }
    action = actions.get(candidate.category, ("Consider a short visit; verify access before leaving.", "Рассмотрите короткий осмотр; перед выходом уточните доступ."))[0 if english else 1]
    return " ".join(reasons), action, warnings


def recommend(request: RecommendRequest, db_path: str | Path | None = None, *,
              evaluation_time: datetime | None = None, weather_override: Weather | None = None,
              use_llm: bool = True) -> RecommendResponse:
    _validate_request(request)
    origin = resolve_origin(request)
    if evaluation_time is not None and not isinstance(evaluation_time, datetime):
        raise ValueError("Evaluation time must be a datetime")
    if weather_override is not None and not isinstance(weather_override, Weather):
        raise ValueError("Weather override must be a Weather record")
    if not isinstance(use_llm, bool):
        raise ValueError("use_llm must be a boolean")
    local_time = evaluation_time if evaluation_time is not None else _request_time(request)
    local_time = local_time.replace(tzinfo=TIMEZONE) if local_time.tzinfo is None else local_time.astimezone(TIMEZONE)
    weather = weather_override if weather_override is not None else get_weather(request.weather_mode, *origin)
    english = request.language.casefold().startswith("en")
    limitations = [
        "Distances and walking times are geometric estimates, not verified routes; barriers and access are unknown." if english else "Расстояния и время пешком — геометрические оценки, не проверенные маршруты; препятствия и доступ неизвестны.",
        "Each card is a separate option: travel + visit + 5-minute reserve, including estimated return when selected." if english else "Каждая карточка — отдельный вариант: путь + посещение + запас 5 минут; обратный путь включён, если выбран.",
        "Supported weekly hours filter the selected time and estimated visit; complex schedules stay unknown. No live availability is verified." if english else "Поддерживаемые недельные графики ограничивают выбранное время и расчётное посещение; сложные графики остаются неизвестными. Живая доступность не проверена.",
        "Outdoor exposure is a model estimate for the first displayed option, including alternatives; likely indoor status is uncertain." if english else "Время снаружи — модельная оценка первого показанного варианта, включая альтернативы; предполагаемое помещение не подтверждено.",
    ]
    response = RecommendResponse(weather=weather, time_is_simulated=request.time_mode == "simulated",
                                 limitations=limitations, local_datetime=local_time.isoformat())
    nighttime = local_time.hour >= 22 or local_time.hour < 6
    if nighttime:
        response.limitations.append("Late local time: independently verify access, transport and venue availability; listed hours are not live confirmation." if english else "Позднее местное время: самостоятельно проверьте доступ, транспорт и возможность посещения; расписание не является живым подтверждением.")
    if request.time_mode == "simulated" and request.weather_mode == "live":
        response.limitations.append("Live weather describes current conditions, not the simulated date." if english else "Текущая погода относится к реальным условиям, а не к смоделированной дате.")
    if request.location_preset == "airport" and has_flight_deadline(request):
        response.general_message = (
            "With a flight deadline, no excursion from the airport is recommended. Check airline check-in and boarding requirements; POI data does not establish terminal, landside or airside access."
            if english else "При ограничении до вылета не предлагаем покидать аэропорт. Уточните сроки регистрации и посадки у авиакомпании; база POI не подтверждает доступ из терминала, до или после контроля."
        )
        return response
    intents = parse_intents(request.query, request.interests)
    try:
        candidates = get_candidates(origin, request.duration_minutes, request.return_to_start, db_path, intents,
                                    evaluation_time=local_time)
    except DatabaseUnavailable:
        response.general_message = ("POI data is unavailable. Run: python -m ingestion.build_database" if english else "База мест недоступна. Выполните: python -m ingestion.build_database")
        return response
    ranked = rank_candidates(candidates, intents, weather, request.climate_shield_enabled,
                             request.duration_minutes, request.return_to_start)
    direct = [candidate for candidate in ranked if is_direct_match(candidate, intents)][:3]
    alternatives = [candidate for candidate in ranked if not is_direct_match(candidate, intents)][:3 - len(direct)]
    selected = direct + alternatives
    if not selected:
        if intents & {"power_outlets", "wifi", "accessibility"}:
            response.general_message = ("No place with the required confirmed features fits the time and weather constraints. Unknown features are not treated as confirmed." if english else "В пределах времени и погодных ограничений нет места с подтверждёнными обязательными удобствами. Неизвестные свойства не считаются подтверждёнными.")
        else:
            response.general_message = ("No place fits the time, access and selected weather constraints. Try another origin, more time, or check the available source data." if english else "Нет места, подходящего по времени, доступу и выбранным погодным ограничениям. Попробуйте другую отправную точку, увеличьте время или проверьте исходные данные.")
        return response
    if not direct and alternatives:
        response.general_message = ("No direct category matches remain after time, opening-hours and weather constraints. The separate alternatives below are in other categories and keep all required features." if english else "После ограничений времени, расписания и погоды прямых совпадений по категории нет. Ниже отдельно показаны альтернативы в других категориях с сохранением обязательных удобств.")
    generated = generate_explanations(selected, request, weather) if use_llm else None
    direct_ids = {candidate.id for candidate in direct}
    for candidate in selected:
        reason, action, warnings = _template(candidate, intents, weather, english)
        if nighttime:
            warnings.append("Late local time: confirm access and opening details before leaving." if english else "Позднее местное время: перед выходом уточните доступ и расписание.")
        if generated is not None:
            text = generated[candidate.id]
            reason = text["reason"] if candidate.id in direct_ids else f"{reason} {text['reason']}"
            action = text["action"]
            warnings.extend(text["warnings"])
        card = Recommendation(
            poi_id=candidate.id, name=candidate.name, category=candidate.category, lat=candidate.lat, lon=candidate.lon,
            distance_m=round(candidate.distance_m, 1), travel_minutes_estimated=round(candidate.travel_minutes, 1),
            visit_minutes_estimated=candidate.visit_minutes, reason=reason, action=action,
            opening_note=_opening_note(candidate, english), indoor_status=candidate.indoor_status,
            source=candidate.source, source_url=candidate.source_url, warnings=warnings,
            total_minutes_estimated=round(candidate.total_minutes, 1),
            opening_status=candidate.opening_status,
            description=candidate.description, description_source=candidate.description_source,
            opening_hours_source_url=candidate.opening_hours_source_url,
            opening_hours_checked_at=candidate.opening_hours_checked_at,
        )
        if not all(math.isfinite(value) for value in (card.lat, card.lon, card.distance_m, card.travel_minutes_estimated, card.total_minutes_estimated)):
            continue
        (response.recommendations if candidate.id in direct_ids else response.alternatives).append(card)
    response.estimated_outdoor_minutes = round(estimated_outdoor_minutes(selected[0], request.return_to_start), 1)
    response.answer_mode = "llm" if generated is not None else "template"
    return response
