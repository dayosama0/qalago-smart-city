"""Responsive QalaGo presentation, backed only by real recommendation calls."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime
from html import escape
import hashlib
import json
import sqlite3
from urllib.parse import urlparse

import folium
import streamlit as st
from streamlit_folium import st_folium

from config import DB_PATH, PRESETS, TIMEZONE
from core.links import get_2gis_search_url
from core.models import RecommendRequest, RecommendResponse
from core.recommend import recommend


INTERESTS = {
    "Архитектура": "architecture", "Природа": "nature", "С детьми": "children",
    "Кофе": "coffee", "Тишина": "quiet", "Необычное": "unusual", "Музеи": "museum",
}
WEATHER_LABELS = {
    "clear": "Ясно · симуляция", "wind": "Сильный ветер · симуляция",
    "rain": "Дождь · симуляция", "cold": "Мороз · симуляция",
    "live": "Текущая погода · Open-Meteo",
}
INDOOR_LABELS = {
    "confirmed_indoor": "Помещение · указано в источнике",
    "likely_indoor": "Вероятно в помещении",
    "outdoor": "На улице", "unknown": "Формат места неизвестен",
}
CATEGORY_LABELS = {
    "cafe": "Кафе", "restaurant": "Ресторан", "museum": "Музей", "park": "Парк",
    "garden": "Сад", "playground": "Детская площадка", "attraction": "Достопримечательность",
    "viewpoint": "Смотровая точка", "gallery": "Галерея", "library": "Библиотека",
    "mall": "Торговый центр", "arts_centre": "Культурный центр",
}
DEFAULT_CONTROLS = {
    "origin": "expo", "duration": 60, "interests": ["Архитектура"], "query": "",
    "strict_outlets": False, "return_to_start": False, "flight_constraint": False,
    "climate_shield": True, "weather_mode": "clear", "time_mode": "live",
}
SCENARIOS = {
    "walk": {"label": "Гуляю час", "origin": "expo", "duration": 60,
             "interests": ["Архитектура"], "query": "Хочу прогуляться час и посмотреть архитектуру"},
    "child": {"label": "С ребёнком", "origin": "central_park", "duration": 120,
              "interests": ["С детьми", "Природа", "Музеи"], "query": "Парк или музей для прогулки с ребёнком"},
    "wind": {"label": "Сильный ветер", "origin": "expo", "duration": 60,
             "interests": ["Природа"], "query": "Природа и парки", "weather_mode": "wind"},
    "flight": {"label": "Перед вылетом", "origin": "airport", "duration": 120,
               "interests": [], "query": "Два часа до вылета, хочу посмотреть город", "flight_constraint": True},
}


def displayed_options(response: RecommendResponse) -> list:
    return [*response.recommendations, *getattr(response, "alternatives", [])]


def request_fingerprint(request: RecommendRequest) -> str:
    return hashlib.sha256(json.dumps(asdict(request), sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def snapshot_stats() -> dict:
    if not DB_PATH.is_file():
        return {"error": "Снимок данных ещё не создан."}
    try:
        with sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True) as connection:
            row = connection.execute(
                "SELECT COUNT(*), "
                "SUM(CASE WHEN TRIM(COALESCE(opening_hours, '')) != '' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN TRIM(COALESCE(description, '')) != '' THEN 1 ELSE 0 END), "
                "MAX(fetched_at) FROM pois"
            ).fetchone()
        return {"count": row[0], "hours": row[1] or 0,
                "descriptions": row[2] or 0, "fetched_at": row[3]}
    except sqlite3.Error:
        return {"error": "Снимок SQLite недоступен или имеет неподходящую схему."}


def safe_web_url(value: str) -> str | None:
    parsed = urlparse(value)
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else None


def render_sidebar(stats: dict) -> None:
    with st.sidebar:
        st.markdown("## 🧭 QalaGo")
        st.caption("Реальные места. Понятные ограничения.")
        if "error" in stats:
            st.warning(stats["error"])
        else:
            st.metric("Мест в снимке OSM", stats["count"])
        with st.expander("Прозрачность данных"):
            if "error" not in stats:
                st.write(f"С расписанием: **{stats['hours']}**")
                st.write(f"С описанием: **{stats['descriptions']}**")
                st.caption("Наличие атрибута — не подтверждение актуальной доступности.")
                if stats["fetched_at"]:
                    st.caption(f"Последняя загрузка: {stats['fetched_at']}")
                    try:
                        fetched = datetime.fromisoformat(stats["fetched_at"].replace("Z", "+00:00"))
                        if fetched.tzinfo:
                            age = max(0, (datetime.now(TIMEZONE) - fetched).days)
                            st.caption(f"Возраст последней загрузки: {age} дн. Данные могли измениться.")
                    except (TypeError, ValueError):
                        pass
            st.caption("© OpenStreetMap contributors · ODbL 1.0")
            st.markdown("[Источник и лицензия OSM](https://www.openstreetmap.org/copyright)")
            st.caption("Покрытие ограничено районами снимка. Нет гарантии полного каталога Астаны.")
        st.caption("Без GPS и истории перемещений. Запросы и координаты не записываются в базу.")
        st.caption("API-ключ не нужен. Карта и внешние ссылки используют интернет.")


def render_conditions_badge(request: RecommendRequest) -> None:
    weather = "ТЕКУЩАЯ ПОГОДА · Open-Meteo" if request.weather_mode == "live" else f"СИМУЛЯЦИЯ ПОГОДЫ · {WEATHER_LABELS[request.weather_mode].split(' · ')[0]}"
    clock = "СИМУЛЯЦИЯ ВРЕМЕНИ" if request.time_mode == "simulated" else "РЕАЛЬНЫЕ ЧАСЫ"
    st.caption(f"{weather}  |  {clock} · Астана, UTC+5")
    if request.time_mode == "simulated" and request.weather_mode == "live":
        st.warning("Часы относятся к сценарию, а погода — к текущему моменту.")


def render_weather(response: RecommendResponse, request: RecommendRequest) -> None:
    weather = response.weather
    status = {"normal": "Обычные условия", "caution": "Неблагоприятные условия",
              "severe": "Сложные условия", "unknown": "Погода неизвестна"}.get(weather.status, weather.status)
    with st.container(border=True):
        st.markdown(f"**{status} · Climate Shield {'включён' if request.climate_shield_enabled else 'выключен'}**")
        kind = "СИМУЛЯЦИЯ" if weather.is_simulated else "ТЕКУЩИЕ ДАННЫЕ"
        st.caption(f"{kind} · {weather.source}" + (f" · {weather.observed_at}" if weather.observed_at else ""))
        values = []
        for label, value, unit in (("Ощущается", weather.apparent_temperature, "°C"),
                                   ("Ветер", weather.wind_speed, "м/с"),
                                   ("Осадки", weather.precipitation, "мм")):
            if value is not None:
                values.append(f"{label}: {value:g} {unit}")
        if values:
            st.caption(" · ".join(values))
        if weather.status in {"caution", "severe", "unknown"}:
            st.caption("Проверьте условия перед выходом. Shield и оценки времени не гарантируют безопасность.")
        clock = "СИМУЛЯЦИЯ ВРЕМЕНИ" if response.time_is_simulated else "ВРЕМЯ РАСЧЁТА"
        st.caption(f"{clock} · {response.local_datetime or 'Asia/Almaty'}")
        exposure = f"≈ {response.estimated_outdoor_minutes:.1f} мин на улице у первого варианта" if displayed_options(response) else "Подходящего варианта нет"
        mode = {"template": "Без LLM", "llm": "Пояснение OpenAI", "empty": "Нет совпадений"}.get(response.answer_mode, response.answer_mode)
        st.caption(f"{exposure} · {mode}")


def render_map(response: RecommendResponse, request: RecommendRequest, map_key: str) -> None:
    if request.location_preset == "custom":
        origin, origin_name = (request.latitude, request.longitude), "Выбранная точка"
    else:
        preset = PRESETS[request.location_preset]
        origin, origin_name = (preset["lat"], preset["lon"]), preset["name"]
    city_map = folium.Map(location=origin, zoom_start=14, control_scale=True)
    folium.Marker(origin, tooltip=escape(origin_name), icon=folium.Icon(color="green", icon="home")).add_to(city_map)
    bounds = [origin]
    direct_count = len(response.recommendations)
    for index, item in enumerate(displayed_options(response), 1):
        point = (item.lat, item.lon)
        bounds.append(point)
        alternative = index > direct_count
        label = f"{index}. {escape(item.name)}" + (" · запасной вариант" if alternative else "")
        folium.Marker(point, tooltip=label, popup=folium.Popup(escape(item.name), max_width=250),
                      icon=folium.Icon(color="orange" if alternative else "blue", icon="info-sign")).add_to(city_map)
    if len(bounds) > 1:
        city_map.fit_bounds(bounds, padding=(35, 35), max_zoom=15)
    st_folium(city_map, height=320, use_container_width=True, returned_objects=[], key=f"map-{map_key}")
    st.caption("Синие точки — совпадения, оранжевые — запасные варианты. Точка может быть центром здания, а не входом. Маршрут не построен.")


def shared_warnings(response: RecommendResponse) -> list[str]:
    counts = Counter(warning for item in displayed_options(response) for warning in set(item.warnings))
    return sorted(warning for warning, count in counts.items() if count > 1)


def opening_summary(item) -> str:
    if getattr(item, "opening_status", "unknown") == "listed_open":
        return "По указанному расписанию визит возможен. Фактический доступ не проверен."
    return "Доступность в выбранное время не подтверждена."


def render_card(item, index: int, request: RecommendRequest, shared: list[str]) -> None:
    with st.container(border=True):
        st.subheader(f"{index}. {item.name}")
        st.caption(f"{CATEGORY_LABELS.get(item.category, item.category)} · {INDOOR_LABELS.get(item.indoor_status, item.indoor_status)}")
        if getattr(item, "description", None):
            st.caption(item.description)
        st.markdown(f"**≈ {item.travel_minutes_estimated:.0f} мин пешком** · {item.distance_m:.0f} м по прямой · {item.visit_minutes_estimated} мин на месте")
        if item.total_minutes_estimated:
            st.caption(f"Всего с резервом{' и возвращением' if request.return_to_start else ''}: ≈ {item.total_minutes_estimated:.0f} из {request.duration_minutes} мин")
        st.write(item.reason)
        st.write(f"Идея: {item.action}")
        st.caption(opening_summary(item))
        st.markdown(f"[Найти в 2ГИС ↗]({get_2gis_search_url(item.name)})")
        with st.expander("Источники и ограничения"):
            source_url = safe_web_url(item.source_url)
            if source_url:
                st.markdown(f"[Источник: {escape(item.source)}]({source_url})")
            else:
                st.write(f"Источник: {item.source}")
            description_url = safe_web_url(getattr(item, "description_source", None) or "")
            if description_url:
                st.markdown(f"[Источник краткого описания]({description_url})")
            st.write(item.opening_note)
            hours_url = safe_web_url(getattr(item, "opening_hours_source_url", None) or "")
            if hours_url and hours_url != source_url:
                st.markdown(f"[Источник расписания]({hours_url})")
            if getattr(item, "opening_hours_checked_at", None):
                st.caption(f"Расписание · дата источника / проверки: {item.opening_hours_checked_at}")
            for warning in dict.fromkeys(item.warnings):
                if warning not in shared:
                    st.caption(warning)
            if any(warning in shared for warning in item.warnings):
                st.caption("Общие для нескольких мест предупреждения приведены под результатами.")
            st.caption("2ГИС — поиск по названию и Астане, не гарантированная карточка конкретной организации. Данные 2ГИС не собираются.")


def render_results(response: RecommendResponse, request: RecommendRequest, fingerprint: str, *, weather: bool = True) -> None:
    if weather:
        render_weather(response, request)
    if response.general_message:
        st.info(response.general_message)
    options = displayed_options(response)
    shared = shared_warnings(response)
    if response.recommendations:
        st.markdown("### По вашим интересам")
        for index, item in enumerate(response.recommendations, 1):
            render_card(item, index, request, shared)
    if getattr(response, "alternatives", []):
        st.markdown("### Запасные варианты")
        st.caption("Эти места не совпадают с выбранными категориями. Проверьте, подходят ли они вам как альтернатива.")
        for index, item in enumerate(response.alternatives, len(response.recommendations) + 1):
            render_card(item, index, request, shared)
    if not options and not response.general_message:
        st.info("Подходящих мест не найдено. Попробуйте другой район, больше времени или менее строгие условия.")
    if options:
        st.caption("Карточки — отдельные варианты, не общий маршрут. Время и расстояния приблизительны.")
        with st.expander(f"Карта · {len(options)} места"):
            render_map(response, request, fingerprint)
    with st.expander("Общие источники и ограничения"):
        for note in dict.fromkeys([*shared, *response.limitations]):
            st.caption(note)
        if response.weather.note:
            st.caption(response.weather.note)
        st.caption("© OpenStreetMap contributors · ODbL. Свежесть снимка — в разделе «Прозрачность данных» боковой панели.")


def render_comparison(comparison, request: RecommendRequest, fingerprint: str) -> None:
    st.markdown("## Сравнение Climate Shield")
    st.write(comparison.explanation)
    st.caption(f"Один запрос, одна погода и время расчёта: {comparison.evaluated_at}. Шаблонные объяснения изолируют влияние Shield.")
    difference = comparison.outdoor_difference_minutes
    if difference is None:
        st.caption("Изменение минут на улице не рассчитывается: на одной из сторон нет варианта.")
    elif difference > 0:
        st.caption(f"У первых показанных вариантов оценка с Shield ниже на {difference:.1f} мин. Это не измерение и не гарантия улучшения.")
    elif difference < 0:
        st.caption(f"У первого варианта с Shield оценка снаружи выше на {abs(difference):.1f} мин. Данные не обещают улучшение.")
    else:
        st.caption("Оценочное время снаружи у первых вариантов одинаково.")
    for column, enabled, response in zip(st.columns(2), (False, True), (comparison.off, comparison.on)):
        with column:
            st.markdown(f"### Shield {'включён' if enabled else 'выключен'}")
            first_is_alternative = not response.recommendations and bool(getattr(response, "alternatives", []))
            label = "На улице · первый запасной вариант" if first_is_alternative else "На улице · первое совпадение"
            st.metric(label, f"≈ {response.estimated_outdoor_minutes:.1f} мин" if displayed_options(response) else "Нет варианта")
            st.caption(f"{'СИМУЛЯЦИЯ ПОГОДЫ' if response.weather.is_simulated else 'ТЕКУЩАЯ ПОГОДА'} · {response.weather.source}" + (f" · {response.weather.observed_at}" if response.weather.observed_at else ""))
            render_results(response, replace(request, climate_shield_enabled=enabled), f"{fingerprint}-{enabled}", weather=False)


def choose_scenario(name: str) -> None:
    # Callback executes before widgets on the next run, so controls and the
    # fresh backend request always agree. No stored recommendation is reused.
    values = {**DEFAULT_CONTROLS, **SCENARIOS[name]}
    for key in DEFAULT_CONTROLS:
        value = values[key]
        st.session_state[key] = list(value) if isinstance(value, list) else value
    st.session_state["qalago_pending_action"] = "generate"


def build_controls() -> RecommendRequest:
    for key, value in DEFAULT_CONTROLS.items():
        if key not in st.session_state:
            st.session_state[key] = list(value) if isinstance(value, list) else value
    start_col, duration_col = st.columns([1.6, 1])
    with start_col:
        preset = st.selectbox("Откуда начнём?", list(PRESETS) + ["custom"], key="origin",
                              format_func=lambda key: PRESETS[key]["name"] if key in PRESETS else "Свои координаты · вручную")
    with duration_col:
        duration = st.radio("Сколько времени?", [30, 60, 120], key="duration", format_func=lambda minutes: f"{minutes} мин", horizontal=True)
    latitude = longitude = None
    if preset == "custom":
        lat_col, lon_col = st.columns(2)
        latitude = lat_col.number_input("Широта", min_value=-90.0, max_value=90.0, value=51.1282, format="%.5f", key="latitude")
        longitude = lon_col.number_input("Долгота", min_value=-180.0, max_value=180.0, value=71.4304, format="%.5f", key="longitude")
    query = st.text_input("Что хочется?", placeholder="Например: тихое кафе или короткая прогулка по парку", max_chars=1000, key="query")
    selected_interests = st.multiselect("Интересы", list(INTERESTS), key="interests")
    with st.expander("Погода, время и дополнительные условия"):
        shield = st.toggle("Climate Shield", key="climate_shield", help="Меняет отбор в неблагоприятную погоду. Не гарантирует безопасность.")
        weather_mode = st.selectbox("Погода", list(WEATHER_LABELS), key="weather_mode", format_func=WEATHER_LABELS.get)
        time_mode = st.radio("Местное время · Asia/Almaty", ["live", "simulated"], key="time_mode",
                             format_func=lambda value: "Сейчас" if value == "live" else "Симуляция", horizontal=True)
        simulated_datetime = None
        if time_mode == "simulated":
            now = datetime.now(TIMEZONE)
            date_col, time_col = st.columns(2)
            chosen_date = date_col.date_input("Дата сценария", value=now.date(), key="simulated_date")
            chosen_time = time_col.time_input("Время сценария", value=now.replace(hour=22, minute=0, second=0, microsecond=0).time(), key="simulated_time")
            simulated_datetime = datetime.combine(chosen_date, chosen_time).replace(tzinfo=TIMEZONE).isoformat()
        outlets = st.checkbox("Обязательно подтверждённая розетка", key="strict_outlets", help="Неизвестное наличие не считается подтверждением; результат может быть пустым.")
        return_trip = st.checkbox("Учесть возвращение в исходную точку", key="return_to_start")
        flight = st.checkbox("Время ограничено вылетом", key="flight_constraint", help="Для аэропорта действует консервативное ограничение. Это не расчёт регистрации и посадки.")
        st.caption("Только пешком. Симуляция погоды не является прогнозом; часы из OSM не гарантируют фактический доступ.")
    interests = [INTERESTS[label] for label in selected_interests]
    if outlets:
        interests.append("power_outlets")
    return RecommendRequest(location_preset=preset, latitude=latitude, longitude=longitude,
                            query=query, interests=interests, duration_minutes=duration,
                            return_to_start=return_trip, climate_shield_enabled=shield,
                            weather_mode=weather_mode, time_mode=time_mode,
                            simulated_datetime=simulated_datetime, flight_constraint=flight)


def main() -> None:
    st.markdown("""<style>
    .block-container { max-width: 1100px; padding-top: 2rem; padding-bottom: 3rem; }
    h1, h2, h3 { overflow-wrap: anywhere; }
    h1 { letter-spacing: -.04em; }
    [data-testid="stMetricValue"] { font-size: 1.65rem; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 16px; }
    [data-testid="stMarkdownContainer"] a { overflow-wrap: anywhere; }
    [data-testid="stColumn"] { min-width: 0; }
    @media (max-width: 640px) {
      .block-container { padding: 1.2rem 1rem 2rem; }
      h1 { font-size: 2.2rem !important; }
      h2 { font-size: 1.5rem !important; }
      h3 { font-size: 1.2rem !important; }
      [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
      [data-testid="stColumn"] { flex: 1 1 100% !important; width: 100% !important; min-width: 0 !important; }
      .st-key-quick_scenarios [data-testid="stHorizontalBlock"] { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .5rem; }
    }
    </style>""", unsafe_allow_html=True)
    stats = snapshot_stats()
    render_sidebar(stats)
    st.caption("АСТАНА · МЕСТА ПО ВАШЕМУ ВРЕМЕНИ")
    st.title("QalaGo")
    st.write("Умные прогулки по Астане — с учётом интересов и погоды.")
    with st.container(border=True):
        request = build_controls()
        render_conditions_badge(request)
    fingerprint = request_fingerprint(request)
    data_ready = "error" not in stats and stats.get("count", 0) > 0
    if not data_ready:
        st.warning("Нужен подлинный SQLite-снимок. Сохранённые публичные данные можно собрать командой:")
        st.code("python -m ingestion.build_database --offline", language="bash")
    primary, secondary = st.columns([1, 1])
    generate_clicked = primary.button("Подобрать прогулку", type="primary", use_container_width=True, disabled=not data_ready, key="generate")
    compare_clicked = secondary.button("Сравнить с Climate Shield", use_container_width=True, disabled=not data_ready, key="compare")
    with st.container(key="quick_scenarios"):
        st.caption("Попробуйте готовый запрос · параметры и расчёт настоящие")
        for column, (name, scenario) in zip(st.columns(4), SCENARIOS.items()):
            column.button(scenario["label"], key=f"scenario_{name}", use_container_width=True,
                          disabled=not data_ready, on_click=choose_scenario, args=(name,))
    pending_action = st.session_state.pop("qalago_pending_action", None)
    if generate_clicked or pending_action == "generate":
        try:
            with st.spinner("Подбираем места из локального снимка…"):
                response = recommend(request, db_path=DB_PATH)
            st.session_state["qalago_result"] = (fingerprint, response, request)
            st.session_state.pop("qalago_comparison", None)
        except Exception:
            st.session_state.pop("qalago_result", None)
            st.session_state.pop("qalago_comparison", None)
            st.error("Подбор недоступен. Проверьте снимок командой python -m ingestion.build_database --offline и повторите попытку.")
    elif compare_clicked:
        try:
            from core.comparison import compare_climate_shield
            with st.spinner("Считаем OFF и ON с одной погодой и одним временем…"):
                comparison = compare_climate_shield(request, db_path=DB_PATH)
            st.session_state["qalago_comparison"] = (fingerprint, comparison, request)
            st.session_state.pop("qalago_result", None)
        except Exception:
            st.session_state.pop("qalago_comparison", None)
            st.session_state.pop("qalago_result", None)
            st.error("Сравнение недоступно. Повторите запрос или используйте обычный подбор.")
    stored = st.session_state.get("qalago_result")
    compared = st.session_state.get("qalago_comparison")
    if compared and compared[0] == fingerprint:
        render_comparison(compared[1], compared[2], fingerprint)
    elif stored and stored[0] == fingerprint:
        render_results(stored[1], stored[2], fingerprint)
    elif stored or compared:
        st.info("Условия изменились. Нажмите «Подобрать прогулку» или сравните заново.")
    else:
        st.caption("До трёх реальных мест из OSM. Без API-ключа и отслеживания GPS.")
