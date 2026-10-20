"""Unified UI/backend entry point for deterministic structured RAG."""
from datetime import datetime, timedelta
from dataclasses import replace
from core.ai_search import AIUnavailable, plan_query, filter_requirements, select_places
import math
from pathlib import Path

from config import TIMEZONE
from core.clock import local_now
from core.geo import resolve_origin
from core.hours import visit_status
from core.models import RecommendRequest, RecommendResponse, Recommendation
from core.ranking import estimated_outdoor_minutes, rank_candidates
from core.retrieval import DatabaseUnavailable, INTENT_CATEGORIES, get_candidates, has_flight_deadline, parse_intents
from core.weather import get_weather

MAX_RESULTS = 20


def _request_time(request: RecommendRequest) -> datetime:
    if request.time_mode == "live":
        return local_now()
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
    if type(request.group_size) is not int or not 1 <= request.group_size <= 5:
        raise ValueError("Group size must be an integer between 1 and 5")
    if (not isinstance(request.member_preferences, list)
            or len(request.member_preferences) > request.group_size
            or any(not isinstance(value, str) or len(value) > 300 for value in request.member_preferences)):
        raise ValueError("Provide at most one preference per member, up to 300 characters each")
    if request.language not in {"auto", "ru", "kk", "en"}:
        raise ValueError("Unsupported recommendation language")
    if request.weather_mode not in {"live", "clear", "wind", "rain", "cold"}:
        raise ValueError("Unknown weather mode")
    for flag in (request.walking_only, request.return_to_start, request.climate_shield_enabled, request.flight_constraint, request.require_open_hours):
        if not isinstance(flag, bool):
            raise ValueError("Request flags must be booleans")


def _opening_note(candidate, english: bool) -> str:
    freshness = candidate.opening_hours_checked_at or candidate.fetched_at or ("unknown" if english else "неизвестно")
    source = candidate.opening_hours_source or candidate.source
    if candidate.opening_hours:
        if english:
            return f"Listed hours: {candidate.opening_hours}. Current availability not verified. Source: {source}; reference date {freshness}."
        return f"Указанное расписание: {candidate.opening_hours}. Доступность сейчас не проверена. Источник: {source}; дата сведений {freshness}."
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


def recommend(request: RecommendRequest, db_path: str | Path | None = None, *, use_llm: bool = True) -> RecommendResponse:
    _validate_request(request)
    origin = resolve_origin(request)
    local_time = _request_time(request)
    weather = get_weather(request.weather_mode, *origin)
    english = request.language.casefold().startswith("en")
    limitations = [
        "Distances and walking times are geometric estimates, not verified routes; barriers and access are unknown." if english else "Расстояния и время пешком — геометрические оценки, не проверенные маршруты; препятствия и доступ неизвестны.",
        "Each card is a separate option: travel + visit + 5-minute reserve, including estimated return when selected." if english else "Каждая карточка — отдельный вариант: путь + посещение + запас 5 минут; обратный путь включён, если выбран.",
        "Opening schedules are raw source data; simulated time does not verify availability." if english else "Расписание — исходные данные источника; моделирование времени не проверяет доступность.",
        "Outdoor exposure is a model estimate for the first-ranked option; likely indoor status is uncertain." if english else "Время снаружи — модельная оценка первого варианта; предполагаемое помещение не подтверждено.",
    ]
    response = RecommendResponse(weather=weather, time_is_simulated=request.time_mode == "simulated",
                                 limitations=limitations, local_datetime=local_time.isoformat())
    nighttime = local_time.hour >= 22 or local_time.hour < 6
    if nighttime:
        response.limitations.append("Late local time: verify access and transport independently; opening status is based on supported source schedules, not live verification." if english else "Позднее местное время: самостоятельно проверьте доступ и транспорт; статус работы рассчитан по расписанию источника, без проверки на месте.")
    if request.time_mode == "simulated" and request.weather_mode == "live":
        response.limitations.append("Live weather describes current conditions, not the simulated date." if english else "Текущая погода относится к реальным условиям, а не к смоделированной дате.")
    if request.location_preset == "airport" and has_flight_deadline(request):
        response.general_message = (
            "With a flight deadline, no excursion from the airport is recommended. Check airline check-in and boarding requirements; POI data does not establish terminal, landside or airside access."
            if english else "При ограничении до вылета не предлагаем покидать аэропорт. Уточните сроки регистрации и посадки у авиакомпании; база POI не подтверждает доступ из терминала, до или после контроля."
        )
        return response
    plan = None
    ai_failed = False
    if use_llm:
        try:
            plan = plan_query(request)
            if plan.duration_minutes is not None:
                request = replace(request, duration_minutes=min(request.duration_minutes, plan.duration_minutes))
        except AIUnavailable as error:
            if not request.allow_fallback:
                response.answer_mode = "ai_error"
                response.general_message = error.user_message
                return response
            ai_failed = True
    intents = parse_intents(request.query, request.interests)
    try:
        candidates = get_candidates(origin, request.duration_minutes, request.return_to_start, db_path, intents)
    except DatabaseUnavailable:
        response.general_message = ("POI data is unavailable. Run: python -m ingestion.build_database" if english else "База мест недоступна. Выполните: python -m ingestion.build_database")
        return response
    if plan is not None:
        candidates = filter_requirements(candidates, plan)
    ranked = rank_candidates(candidates, intents, weather, request.climate_shield_enabled,
                             request.duration_minutes, request.return_to_start)
    statuses = {candidate.id: visit_status(candidate.opening_hours,
                local_time + timedelta(minutes=candidate.travel_minutes), candidate.visit_minutes)
                for candidate in ranked}
    if request.require_open_hours:
        ranked = [candidate for candidate in ranked if statuses[candidate.id] == "open"]
    # Keep closed options as a clearly marked fallback, after all viable options.
    ranked.sort(key=lambda candidate: statuses[candidate.id] in {"closed", "closes_during_visit"})
    generated = None
    selected = ranked[:MAX_RESULTS]
    if selected and use_llm and not ai_failed:
        try:
            viable = [c for c in ranked if statuses[c.id] not in {"closed", "closes_during_visit"}]
            selection = select_places(viable[:12], request, weather) if viable else None
            choices = selection.recommendations if selection else []
            by_id = {c.id: c for c in viable}
            selected = [by_id[c.poi_id] for c in choices]
            generated = {c.poi_id: {"description": c.description, "reason": c.reason, "action": c.action, "warnings": []} for c in choices}
            response.general_message = selection.message if selection and selection.message else None
        except AIUnavailable as error:
            if not request.allow_fallback:
                response.answer_mode = "ai_error"
                response.general_message = error.user_message
                return response
            ai_failed = True
    if ai_failed:
        response.general_message = "ИИ недоступен. Используется разрешённый вами резервный подбор по правилам."
    if generated is None and request.group_size > 1 and selected:
        group_note = "Резервный режим учитывает общие условия, но не согласует пожелания участников."
        response.general_message = " ".join(filter(None, [response.general_message, group_note]))

    if not selected:
        if request.require_open_hours:
            response.general_message = ("No matching places are open for the entire visit according to available schedules. Try another time or change the search conditions."
                if english else "По выбранным условиям нет мест, открытых по расписанию на всё время посещения. Попробуйте другое время или измените условия поиска.")
        elif plan is not None and plan.max_average_check_kzt is not None:
            response.general_message = "По указанному бюджету подходящие места не найдены. Попробуйте изменить условия поиска."
        elif plan is not None and (plan.categories or plan.coffee_shop_only):
            response.general_message = "По указанным условиям места не найдены. Попробуйте изменить условия поиска."
        elif intents & {"power_outlets", "wifi"}:
            response.general_message = ("No place with the required confirmed features fits the time and weather constraints. Unknown features are not treated as confirmed." if english else "В пределах времени и погодных ограничений нет места с подтверждёнными обязательными удобствами. Неизвестные свойства не считаются подтверждёнными.")
        else:
            response.general_message = ("No place fits the time, access and selected weather constraints. Try another origin, more time, or check the available source data." if english else "Нет места, подходящего по времени, доступу и выбранным погодным ограничениям. Попробуйте другую отправную точку, увеличьте время или проверьте исходные данные.")
        return response

    for candidate in selected:
        reason, action, warnings = _template(candidate, intents, weather, english)
        if nighttime:
            warnings.append("Late local time: confirm access and opening details before leaving." if english else "Позднее местное время: перед выходом уточните доступ и расписание.")
        if generated is not None:
            text = generated[candidate.id]
            reason, action = text["reason"], text["action"]
            warnings.extend(text["warnings"])
        card = Recommendation(
            poi_id=candidate.id, name=candidate.name, category=candidate.category, lat=candidate.lat, lon=candidate.lon,
            distance_m=round(candidate.distance_m, 1), travel_minutes_estimated=round(candidate.travel_minutes, 1),
            visit_minutes_estimated=candidate.visit_minutes, reason=reason, action=action,
            opening_note=_opening_note(candidate, english), indoor_status=candidate.indoor_status,
            source=candidate.source, source_url=candidate.source_url, warnings=warnings,
            total_minutes_estimated=round(candidate.total_minutes, 1),
            opening_hours=candidate.opening_hours, opening_status=statuses[candidate.id],
            opening_hours_source=candidate.opening_hours_source,
            opening_hours_checked_at=candidate.opening_hours_checked_at,
            opening_status_now=visit_status(candidate.opening_hours, local_time, 0),
            arrival_datetime=(local_time + timedelta(minutes=candidate.travel_minutes)).isoformat(),
            description=generated[candidate.id]["description"] if generated is not None else candidate.description,
            description_source="" if generated is not None else candidate.description_source,
        )
        if not all(math.isfinite(value) for value in (card.lat, card.lon, card.distance_m, card.travel_minutes_estimated, card.total_minutes_estimated)):
            continue
        response.recommendations.append(card)
    response.estimated_outdoor_minutes = round(estimated_outdoor_minutes(selected[0], request.return_to_start), 1)
    response.answer_mode = "llm" if generated is not None else "template"
    return response
