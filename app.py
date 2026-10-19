"""QalaGo Streamlit entry point. Reads the shipped snapshot; never ingests on startup."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from html import escape
import hashlib
import json
import os
import sqlite3
from urllib.parse import urlparse

import folium
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import st_folium


st.set_page_config(page_title="QalaGo · Астана", page_icon="🧭", layout="wide")


def load_optional_credentials() -> None:
    """Local/Cloud credentials stay in process memory, outside cached UI state."""
    load_dotenv(override=False)
    for name in ("OPENAI_API_KEY", "OPENAI_MODEL", "OVERPASS_URL", "WEATHER_ENABLED"):
        if os.environ.get(name):
            continue
        try:
            value = st.secrets.get(name)
        except (FileNotFoundError, KeyError):
            value = None
        except Exception:
            # Streamlit versions use distinct missing-secrets exception classes.
            # Missing optional secrets must never stop the no-key application.
            value = None
        if isinstance(value, str) and value:
            os.environ[name] = value


load_optional_credentials()

from config import DB_PATH, PRESETS, TIMEZONE  # noqa: E402
from core.links import get_2gis_search_url  # noqa: E402
from core.models import RecommendRequest, RecommendResponse  # noqa: E402
from core.recommend import recommend  # noqa: E402


INTERESTS = {
    "Архитектура": "architecture",
    "Природа": "nature",
    "С детьми": "children",
    "Кофе": "coffee",
    "Тишина": "quiet",
    "Необычное": "unusual",
    "Музеи": "museum",
}
WEATHER_MODES = {
    "Ясно · симуляция": "clear",
    "Сильный ветер · симуляция": "wind",
    "Дождь · симуляция": "rain",
    "Мороз · симуляция": "cold",
    "Текущая погода · Open-Meteo": "live",
}
INDOOR_LABELS = {
    "confirmed_indoor": "В помещении · есть подтверждение в источнике",
    "likely_indoor": "Вероятно в помещении · вывод по категории",
    "outdoor": "На открытом воздухе",
    "unknown": "Помещение / улица: неизвестно",
}
CATEGORY_LABELS = {
    "cafe": "Кафе", "restaurant": "Ресторан", "museum": "Музей",
    "park": "Парк", "garden": "Сад", "playground": "Детская площадка",
    "attraction": "Достопримечательность", "viewpoint": "Смотровая точка",
    "gallery": "Галерея", "library": "Библиотека", "mall": "Торговый центр",
    "arts_centre": "Культурный центр",
}


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
    return value if urlparse(value).scheme in {"http", "https"} else None


def render_sidebar(stats: dict) -> None:
    with st.sidebar:
        st.markdown("## 🧭 QalaGo")
        st.caption("Астана, которую можно исследовать за свободный час")
        st.divider()
        st.markdown("**Данные, а не догадки**")
        if "error" in stats:
            st.warning(stats["error"])
        else:
            st.metric("Реальных мест в снимке OSM", stats["count"])
            left, right = st.columns(2)
            left.metric("С расписанием", stats["hours"])
            right.metric("С описанием", stats["descriptions"])
            if stats["fetched_at"]:
                st.caption("Последняя загрузка из источника:")
                st.code(stats["fetched_at"], language=None)
                try:
                    fetched = datetime.fromisoformat(stats["fetched_at"].replace("Z", "+00:00"))
                    if fetched.tzinfo is not None:
                        age = max(0, (datetime.now(TIMEZONE) - fetched).days)
                        st.caption(f"Возраст последней загрузки: {age} дн. Данные могли измениться.")
                except (TypeError, ValueError):
                    pass
        st.caption("© OpenStreetMap contributors · ODbL 1.0")
        st.link_button("Источник и лицензия OSM", "https://www.openstreetmap.org/copyright")
        st.divider()
        st.caption("Локация задаётся вручную. GPS не запрашивается. Координаты и запросы не сохраняются в базе.")
        st.caption("Без ключа OpenAI работают детерминированные рекомендации. Карта загружает подложку из интернета.")


def render_weather(response: RecommendResponse, request: RecommendRequest) -> None:
    weather = response.weather
    labels = {"normal": "Обычные условия", "caution": "Осторожность",
              "severe": "Сложные условия", "unknown": "Погода неизвестна"}
    with st.container(border=True):
        first, second, third, fourth = st.columns(4)
        first.metric("Погода", labels.get(weather.status, weather.status))
        second.metric("Climate Shield", "Включён" if request.climate_shield_enabled else "Выключен")
        third.metric("На улице · вариант №1", f"≈ {response.estimated_outdoor_minutes:.0f} мин" if response.recommendations else "—")
        fourth.metric("Объяснения", {"template": "Без LLM", "llm": "OpenAI", "empty": "Нет совпадений"}.get(response.answer_mode, response.answer_mode))
        weather_kind = "СИМУЛЯЦИЯ ПОГОДЫ" if weather.is_simulated else "ТЕКУЩАЯ ПОГОДА"
        st.caption(f"{weather_kind} · источник: {weather.source}" + (f" · время источника: {weather.observed_at}" if weather.observed_at else ""))
        values = []
        for label, value, unit in (("Температура", weather.temperature, "°C"),
                                   ("Ощущается", weather.apparent_temperature, "°C"),
                                   ("Ветер", weather.wind_speed, "м/с"),
                                   ("Порывы", weather.wind_gusts, "м/с"),
                                   ("Осадки", weather.precipitation, "мм")):
            if value is not None:
                values.append(f"{label}: {value:g} {unit}")
        if values:
            st.caption(" · ".join(values))
        if weather.note:
            st.caption(weather.note)
        clock_kind = "СИМУЛЯЦИЯ ВРЕМЕНИ" if response.time_is_simulated else "РЕАЛЬНОЕ МЕСТНОЕ ВРЕМЯ"
        st.caption(f"{clock_kind} · {response.local_datetime or 'Asia/Almaty'} · Asia/Almaty (UTC+5)")
        if request.time_mode == "simulated" and request.weather_mode == "live":
            st.warning("Часы относятся к выбранному сценарию, а погода — к текущим условиям. Это разные моменты времени.")


def render_map(response: RecommendResponse, request: RecommendRequest, fingerprint: str) -> None:
    if request.location_preset == "custom":
        origin = (request.latitude, request.longitude)
        origin_name = "Выбранная точка"
    else:
        preset = PRESETS[request.location_preset]
        origin = (preset["lat"], preset["lon"])
        origin_name = preset["name"]
    city_map = folium.Map(location=origin, zoom_start=14, control_scale=True)
    folium.Marker(origin, tooltip=escape(origin_name), icon=folium.Icon(color="green", icon="home")).add_to(city_map)
    bounds = [origin]
    for index, item in enumerate(response.recommendations, 1):
        point = (item.lat, item.lon)
        bounds.append(point)
        folium.Marker(
            point, tooltip=f"{index}. {escape(item.name)}",
            popup=folium.Popup(escape(item.name), max_width=260),
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(city_map)
    if len(bounds) > 1:
        city_map.fit_bounds(bounds, padding=(45, 45), max_zoom=15)
    st_folium(city_map, height=410, use_container_width=True, returned_objects=[], key=f"map-{fingerprint}")
    st.caption("Маркеры обозначают приблизительные точки OSM. Для зданий это может быть центр, а не вход. Пешеходный маршрут не построен.")


def render_results(response: RecommendResponse, request: RecommendRequest, fingerprint: str) -> None:
    st.markdown("### Варианты для вашей прогулки")
    st.caption("Каждая карточка — отдельный вариант. Они не образуют общий маршрут; время относится к одному месту.")
    render_weather(response, request)
    if response.general_message:
        st.info(response.general_message)
    if not response.recommendations:
        st.info("Подходящих мест с подтверждёнными условиями не найдено. Попробуйте другой район, больший запас времени или менее строгие требования.")
    else:
        for index, item in enumerate(response.recommendations, 1):
            with st.container(border=True):
                st.subheader(f"{index}. {item.name}")
                st.caption(f"{CATEGORY_LABELS.get(item.category, item.category)} · {INDOOR_LABELS.get(item.indoor_status, item.indoor_status)}")
                first, second, third = st.columns(3)
                first.metric("Расстояние по прямой", f"≈ {item.distance_m:.0f} м")
                second.metric("Пешком в одну сторону", f"≈ {item.travel_minutes_estimated:.0f} мин")
                third.metric("На посещение", f"≈ {item.visit_minutes_estimated} мин")
                if item.total_minutes_estimated:
                    st.caption(f"Вся оценка с резервом{' и возвращением' if request.return_to_start else ''}: {item.total_minutes_estimated:.0f} мин из {request.duration_minutes} доступных.")
                st.write(item.reason)
                st.markdown("**Что можно сделать**")
                st.write(item.action)
                st.caption(item.opening_note)
                for warning in item.warnings:
                    st.warning(warning)
                source_col, search_col = st.columns(2)
                source_url = safe_web_url(item.source_url)
                if source_url:
                    source_col.link_button(f"Источник · {item.source}", source_url, use_container_width=True)
                else:
                    source_col.caption(f"Источник: {item.source}")
                search_col.link_button("Найти в 2ГИС ↗", get_2gis_search_url(item.name), use_container_width=True)
                st.caption("2ГИС: ссылка на поиск по названию и городу, а не на проверенную карточку конкретной организации.")
    with st.expander("Карта и ограничения", expanded=bool(response.recommendations)):
        render_map(response, request, fingerprint)
        for limitation in response.limitations:
            st.caption(f"• {limitation}")


def main() -> None:
    st.markdown("""<style>
    .stApp { background: #f6f8fc; }
    h1, h2, h3 { color: #15344b; }
    [data-testid="stMetricValue"] { font-size: 1.35rem; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 16px; }
    </style>""", unsafe_allow_html=True)
    stats = snapshot_stats()
    render_sidebar(stats)
    st.title("QalaGo — Умные прогулки по Астане")
    st.write("Свободное время, ваши интересы и погода → до трёх реальных мест из OpenStreetMap.")
    st.caption("Расстояния и время — геометрические оценки. Перед визитом уточните доступ, часы работы и фактические условия.")

    with st.container(border=True):
        left, right = st.columns([1.3, 1])
        with left:
            preset = st.selectbox("Откуда начнём?", list(PRESETS) + ["custom"],
                                  format_func=lambda key: PRESETS[key]["name"] if key in PRESETS else "Свои координаты · вручную")
            latitude = longitude = None
            if preset == "custom":
                lat_col, lon_col = st.columns(2)
                latitude = lat_col.number_input("Широта", min_value=-90.0, max_value=90.0, value=51.1282, format="%.5f")
                longitude = lon_col.number_input("Долгота", min_value=-180.0, max_value=180.0, value=71.4304, format="%.5f")
            duration = st.radio("Сколько времени есть?", [30, 60, 120], index=1,
                                format_func=lambda minutes: f"{minutes} мин", horizontal=True)
            selected_interests = st.multiselect("Что интересно?", list(INTERESTS), default=["Архитектура"])
            query = st.text_area("Пожелания", placeholder="Например: хочу спокойно погулять и посмотреть архитектуру", max_chars=1000, height=90)
            outlets = st.checkbox("Обязательно подтверждённая розетка", help="Неизвестное наличие розеток не считается подтверждением. Результат может быть пустым.")
            return_trip = st.checkbox("Учесть возвращение в исходную точку")
            flight = st.checkbox("Время ограничено вылетом", help="Для аэропорта действует консервативное ограничение: без поездки в центр. Это не расчёт времени посадки и досмотра.")
        with right:
            st.markdown("**Условия прогулки**")
            shield = st.toggle("Climate Shield", value=True, help="Меняет фильтрацию и приоритеты при неблагоприятной погоде. Не гарантирует безопасность.")
            weather_label = st.selectbox("Погода", list(WEATHER_MODES))
            weather_mode = WEATHER_MODES[weather_label]
            if weather_mode != "live":
                st.info("СИМУЛЯЦИЯ ПОГОДЫ · воспроизводимый сценарий, не прогноз.")
            else:
                st.caption("Текущие условия Open-Meteo. Если сервис недоступен, состояние будет «неизвестно».")
            time_label = st.radio("Местное время · Asia/Almaty", ["Сейчас", "Симуляция"], horizontal=True)
            time_mode = "live" if time_label == "Сейчас" else "simulated"
            simulated_datetime = None
            if time_mode == "simulated":
                now = datetime.now(TIMEZONE)
                date_col, time_col = st.columns(2)
                chosen_date = date_col.date_input("Дата сценария", value=now.date())
                chosen_time = time_col.time_input("Время сценария", value=now.replace(hour=22, minute=0, second=0, microsecond=0).time())
                simulated_datetime = datetime.combine(chosen_date, chosen_time).replace(tzinfo=TIMEZONE).isoformat()
                st.caption("СИМУЛЯЦИЯ ВРЕМЕНИ · часы работы из OSM не подтверждают доступность в этот момент.")
            if time_mode == "simulated" and weather_mode == "live":
                st.warning("Выбраны часы сценария и погода текущего момента.")
            st.caption("Режим передвижения: пешком. Нет автоматического GPS, автомобильного маршрута или расчёта досмотра аэропорта.")

    interests = [INTERESTS[label] for label in selected_interests]
    if outlets:
        interests.append("power_outlets")
    request = RecommendRequest(
        location_preset=preset, latitude=latitude, longitude=longitude,
        query=query, interests=interests, duration_minutes=duration,
        return_to_start=return_trip, climate_shield_enabled=shield,
        weather_mode=weather_mode, time_mode=time_mode,
        simulated_datetime=simulated_datetime, flight_constraint=flight,
    )
    # A changed control invalidates displayed results. Never reuse a previous
    # response as if it belonged to the new origin/weather/time/constraints.
    fingerprint = hashlib.sha256(json.dumps(asdict(request), sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    data_ready = "error" not in stats and stats.get("count", 0) > 0
    if not data_ready:
        st.warning("Для подбора нужен настоящий снимок OSM. В корне проекта выполните команду ниже; если raw-снимок уже есть, добавьте --offline.")
        st.code("python -m ingestion.build_database", language="bash")
    if st.button("Подобрать прогулку", type="primary", use_container_width=True, disabled=not data_ready):
        try:
            with st.spinner("Ищем в локальном снимке и учитываем ограничения…"):
                response = recommend(request, db_path=DB_PATH)
            st.session_state["qalago_result"] = (fingerprint, response, request)
        except Exception:
            st.session_state.pop("qalago_result", None)
            st.error("Подбор сейчас недоступен. Проверьте локальный снимок командой python -m ingestion.build_database --offline и повторите попытку.")
    stored = st.session_state.get("qalago_result")
    if stored and stored[0] == fingerprint:
        render_results(stored[1], stored[2], fingerprint)
    elif stored:
        st.info("Условия изменились. Нажмите «Подобрать прогулку», чтобы пересчитать варианты.")
    else:
        st.caption("Выберите условия и нажмите кнопку. API-ключ для первого запуска не нужен.")


if __name__ == "__main__":
    main()
