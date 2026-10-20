"""QalaGo Streamlit entry point. Reads the shipped snapshot; never ingests on startup."""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
from html import escape
import hashlib
import json
import os
import sqlite3
from urllib.parse import urlparse

import folium
import streamlit as st
from core.result_order import SORT_OPTIONS, sort_results
from dotenv import load_dotenv
from streamlit_folium import st_folium


st.set_page_config(page_title="QalaGo · Астана", page_icon="Q", layout="wide", initial_sidebar_state="collapsed")


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
from core.clock import local_now
from core.links import get_2gis_search_url  # noqa: E402
from core.hours import format_hours
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
        st.markdown("## QalaGo")
        st.caption("Астана, которую можно исследовать за свободный час")
        with st.expander("О данных и приватности"):
            if "error" in stats:
                st.warning(stats["error"])
            else:
                st.caption(f"Мест: {stats['count']} · с расписанием: {stats['hours']} · с описанием: {stats['descriptions']}")
                if stats["fetched_at"]:
                    st.caption(f"Загрузка: {stats['fetched_at']}. Данные могли измениться.")
            st.caption("© OpenStreetMap contributors · ODbL 1.0")
            st.link_button("Источник и лицензия OSM", "https://www.openstreetmap.org/copyright")
            st.caption("Локация задаётся вручную. GPS не запрашивается. Координаты и запросы не сохраняются в базе.")
            st.caption("Без ключа OpenAI работают детерминированные рекомендации. Карта загружает подложку из интернета.")


def render_weather(response: RecommendResponse, request: RecommendRequest) -> None:
    weather = response.weather
    labels = {"normal": "Обычные условия", "caution": "Осторожность",
              "severe": "Сложные условия", "unknown": "Погода неизвестна"}
    summary = []
    if response.local_datetime:
        local = datetime.fromisoformat(response.local_datetime)
        summary.append(f"{'Выбранное время' if response.time_is_simulated else 'Сейчас'} {local:%H:%M} · Астана")
    if weather.is_simulated:
        summary.append("Погода: учебный сценарий")
    elif weather.temperature is not None:
        summary.append(f"{weather.temperature:g} °C")
    else:
        summary.append("Погода недоступна")
    st.caption(" · ".join(summary))
    if weather.status in {"caution", "severe"}:
        st.warning("Погода может помешать прогулке. " + (
            "При подборе отдаём предпочтение помещениям." if request.climate_shield_enabled
            else "Учёт плохой погоды выключен в дополнительных условиях."))
    with st.sidebar:
        st.divider()
        st.markdown("**Условия подбора**")
        if response.local_datetime:
            local = datetime.fromisoformat(response.local_datetime)
            st.markdown(f"**{local:%H:%M}** · {local:%d.%m.%Y} · Астана")
        st.caption("Выбранное время" if response.time_is_simulated else "Сейчас · обновление раз в минуту")
        st.write(labels.get(weather.status, weather.status))
        st.caption("Climate Shield: " + ("включён" if request.climate_shield_enabled else "выключен"))
        if response.recommendations:
            st.caption(f"На улице для первого варианта: ≈ {response.estimated_outdoor_minutes:.0f} мин")
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
        with st.expander("Как сформированы результаты"):
            st.caption("Объяснения: " + {"template": "по правилам, без LLM", "llm": "OpenAI", "empty": "нет совпадений"}.get(response.answer_mode, response.answer_mode))


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
            icon=folium.Icon(color="orange" if item.opening_status in {"closed", "closes_during_visit"} else "blue", icon="info-sign"),
        ).add_to(city_map)
    if len(bounds) > 1:
        city_map.fit_bounds(bounds, padding=(45, 45), max_zoom=15)
    st_folium(city_map, height=410, use_container_width=True, returned_objects=[], key=f"map-{fingerprint}")
    st.caption("Маркеры обозначают приблизительные точки OSM. Для зданий это может быть центр, а не вход. Пешеходный маршрут не построен.")


def render_results(response: RecommendResponse, request: RecommendRequest, fingerprint: str) -> None:
    st.markdown("### Куда пойти")
    render_weather(response, request)
    if response.general_message:
        st.info(response.general_message)
    if not response.recommendations:
        st.error("Мест не найдено по заданным параметрам.")
        st.caption("Увеличьте время, измените точку старта или условия поиска.")
    else:
        count_column, sort_column = st.columns([1, 1])
        with count_column:
            st.markdown(f"**{len(response.recommendations)} мест на выбор**")
        with sort_column:
            order = st.selectbox("Сортировка", options=list(SORT_OPTIONS),
                                format_func=SORT_OPTIONS.get, key="result_sort")
        response = replace(response, recommendations=sort_results(response.recommendations, order))
        st.caption("Выберите одно место для прогулки. Закрытые к приходу — в конце.")
        with st.expander("Посмотреть на карте"):
            render_map(response, request, fingerprint)
        page_key = f"visible_{fingerprint}"
        visible = st.session_state.get(page_key, 6)
        for index, item in enumerate(response.recommendations[:visible], 1):
            if index % 2 == 1:
                columns = st.columns(2, gap="medium")
            closed = item.opening_status in {"closed", "closes_during_visit"}
            with columns[(index - 1) % 2].container(border=True, key=f"place_{index}_{'closed' if closed else 'available'}"):
                st.caption(CATEGORY_LABELS.get(item.category, item.category))
                st.subheader(f"{index}. {item.name}")
                st.markdown(f"**≈ {item.travel_minutes_estimated:.0f} мин пешком** · всего ≈ {item.total_minutes_estimated:.0f} мин")
                if item.description:
                    st.markdown(f'<p class="place-description">{escape(item.description)}</p>', unsafe_allow_html=True)
                labels = {"open": "Открыто по расписанию", "closed": "Закрыто к вашему приходу",
                          "closes_during_visit": "Закроется до конца посещения", "unknown": "Статус работы неизвестен"}
                status_label = labels.get(item.opening_status, labels["unknown"])
                now_status = item.opening_status_now
                if now_status == "closed":
                    status_label = "Закрыто в выбранное время" if response.time_is_simulated else "Сейчас закрыто"
                elif now_status == "open" and not closed:
                    status_label = "Открыто в выбранное время" if response.time_is_simulated else "Сейчас открыто по расписанию"
                if item.opening_status == "closes_during_visit":
                    status_label = "Не успеете до закрытия"
                elif item.opening_status == "closed" and now_status == "open":
                    status_label = "Закроется к вашему приходу"
                tone = "closed" if closed or now_status == "closed" else ("open" if now_status == "open" or item.opening_status == "open" else "unknown")
                st.markdown(f'<div class="hours-panel {tone}"><strong>{escape(status_label)}</strong><div class="hours-text">{escape(format_hours(item.opening_hours))}</div></div>', unsafe_allow_html=True)
                if now_status == "closed" and item.opening_status == "open":
                    st.caption("По расписанию откроется к вашему приходу; времени на посещение хватит.")
                st.link_button("Найти в 2ГИС", get_2gis_search_url(item.name), use_container_width=True)
                with st.expander("Подробнее"):
                    st.caption(INDOOR_LABELS.get(item.indoor_status, item.indoor_status))
                    if item.arrival_datetime:
                        arrival = datetime.fromisoformat(item.arrival_datetime)
                        st.caption(f"Примерный приход: {arrival:%d.%m · %H:%M}")
                    st.caption(f"≈ {item.distance_m:.0f} м по прямой · на посещение ≈ {item.visit_minutes_estimated} мин")
                    st.caption("Общее время включает дорогу, посещение, запас 5 минут" +
                               (" и возвращение." if request.return_to_start else "."))
                    st.write(item.reason)
                    st.write(item.action)
                    st.caption(item.opening_note)
                    hours_url = safe_web_url(item.opening_hours_source)
                    if item.opening_hours and hours_url:
                        st.link_button("Источник расписания", hours_url)
                    description_url = safe_web_url(item.description_source)
                    if description_url:
                        st.link_button("Источник описания", description_url)
                    for warning in item.warnings:
                        st.caption(f"• {warning}")
                    source_url = safe_web_url(item.source_url)
                    if source_url:
                        st.link_button(f"Источник · {item.source}", source_url)
                    else:
                        st.caption(f"Источник: {item.source}")
                    st.caption("2ГИС: поиск по названию и городу; совпадение с организацией не проверено.")
        st.caption(f"Показано {min(visible, len(response.recommendations))} из {len(response.recommendations)}")
        if visible < len(response.recommendations):
            def show_more():
                st.session_state[page_key] = visible + 6
            st.button("Показать ещё места", on_click=show_more, key=f"more_{fingerprint}", use_container_width=True)
    with st.expander("Как рассчитаны время и доступность"):
        st.caption("Часы и расстояния могут отличаться от фактических. Перед выходом проверьте место в справочнике.")
        for limitation in response.limitations:
            st.caption(f"• {limitation}")


@st.fragment(run_every=60)
def render_current_results(fingerprint: str) -> None:
    stored = st.session_state.get("qalago_result")
    if stored and stored[0] == fingerprint:
        _, response, request = stored
        if request.time_mode == "live":
            calculated = datetime.fromisoformat(response.local_datetime) if response.local_datetime else None
            if calculated is None or calculated.replace(second=0, microsecond=0) != local_now().replace(second=0, microsecond=0):
                try:
                    response = recommend(request, db_path=DB_PATH, use_llm=False)
                    st.session_state["qalago_result"] = (fingerprint, response, request)
                except Exception:
                    st.error("Не удалось обновить результаты по текущему времени. Повторите подбор.")
                    return
        render_results(response, request, fingerprint)
    elif stored:
        st.info("Условия изменились. Нажмите «Подобрать прогулку», чтобы пересчитать варианты.")
    else:
        st.caption("Выберите точку старта и время — подберём места, до которых можно дойти пешком.")


def main() -> None:
    st.markdown("""<style>
    .stApp { background: #f7faf9; }
    .block-container { max-width: 1120px; padding-top: 2.5rem; }
    h1, h2, h3 { color: #173c3d; }
    h1 { font-size: 2.5rem; letter-spacing: -.04em; }
    [class*="st-key-place_"] h3 { font-size: 1.35rem; line-height: 1.3; }
    [data-testid="stMetricValue"] { font-size: 1.35rem; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 16px; }
    [class*="st-key-place_"] { background: white; border-radius: 12px; margin: 4px 0 12px; }
    .hours-panel { padding: 8px 0; margin: 0; font-size: .9rem; }
    .hours-panel.open { color: #216348; }
    .hours-panel.closed { color: #884619; }
    .hours-panel.unknown { color: #596b6b; }
    .hours-text { margin-top: 3px; color: #596b6b; font-size: .88rem; line-height: 1.5; }
    .place-description { color: #526665; font-size: .95rem; line-height: 1.5; margin: 0 0 4px; }
    @media (max-width: 640px) {
      .block-container { padding-top: 1.5rem; }
      h1 { font-size: 2rem; }
    }
    </style>""", unsafe_allow_html=True)
    stats = snapshot_stats()
    render_sidebar(stats)
    st.caption("QalaGo · Астана")
    st.title("Куда пойти в свободное время?")
    st.write("Найдите интересное рядом — с учётом времени на дорогу и прогулку.")

    with st.container(border=True):
        left, middle, right = st.columns([1.2, 1, 1.4])
        with left:
            preset = st.selectbox("Откуда начнём?", list(PRESETS) + ["custom"],
                                  format_func=lambda key: PRESETS[key]["name"] if key in PRESETS else "Свои координаты · вручную")
            latitude = longitude = None
            if preset == "custom":
                lat_col, lon_col = st.columns(2)
                latitude = lat_col.number_input("Широта", min_value=-90.0, max_value=90.0, value=51.1282, format="%.5f")
                longitude = lon_col.number_input("Долгота", min_value=-180.0, max_value=180.0, value=71.4304, format="%.5f")
        with middle:
            duration_choice = st.selectbox("Сколько времени есть?", [15, 30, 45, 60, 90, 120, "custom"], index=3,
                                format_func=lambda minutes: "Своё время" if minutes == "custom" else f"{minutes} мин",
                                key="duration_choice")
            duration = (int(st.number_input("Доступное время, минут", min_value=1, max_value=480,
                                           value=75, step=1, key="custom_duration"))
                        if duration_choice == "custom" else duration_choice)
        with right:
            selected_interests = st.multiselect("Что интересно?", list(INTERESTS), default=["Архитектура"],
                                               placeholder="Например, кофе или музеи")
            st.caption("Можно выбрать несколько интересов или убрать все — тогда покажем разные места.")
        with st.expander("Дополнительные условия"):
            query = st.text_area("Пожелания", placeholder="Например: хочу спокойно погулять и посмотреть архитектуру", max_chars=1000, height=90)
            outlets = st.checkbox("Обязательно подтверждённая розетка", key="require_outlets", help="Неизвестное наличие розеток не считается подтверждением. Результат может быть пустым.")
            return_trip = st.checkbox("Вернуться к точке старта", key="return_trip")
            flight = st.checkbox("Время ограничено вылетом", key="flight_constraint", help="Для аэропорта действует консервативное ограничение: без поездки в центр. Это не расчёт времени посадки и досмотра.")
            st.divider()
            shield = st.toggle("Учитывать плохую погоду", value=True, help="При ветре, дожде и морозе отдаём предпочтение помещениям. Защита от погоды не гарантируется.")
            weather_label = st.selectbox("Погода", list(WEATHER_MODES), index=4)
            weather_mode = WEATHER_MODES[weather_label]
            if weather_mode != "live":
                st.info("СИМУЛЯЦИЯ ПОГОДЫ · учебный сценарий, не текущая погода и не прогноз.")
            else:
                st.caption("Текущие условия Open-Meteo. Если сервис недоступен, состояние будет «неизвестно».")
            time_label = st.radio("Когда пойдём? · время Астаны", ["Сейчас", "Симуляция"], horizontal=True, key="time_choice")
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
        st.caption("Пешком · " + ("сейчас" if time_mode == "live" else "выбранное время") +
                   (" · текущая погода" if weather_mode == "live" else " · симуляция погоды") +
                   (" · с возвращением" if return_trip else ""))

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
            with st.spinner("Подбираем места рядом…"):
                response = recommend(request, db_path=DB_PATH)
            st.session_state[f"visible_{fingerprint}"] = 6
            st.session_state["qalago_result"] = (fingerprint, response, request)
        except Exception:
            st.session_state.pop("qalago_result", None)
            st.error("Подбор сейчас недоступен. Проверьте локальный снимок командой python -m ingestion.build_database --offline и повторите попытку.")
    render_current_results(fingerprint)


if __name__ == "__main__":
    main()
