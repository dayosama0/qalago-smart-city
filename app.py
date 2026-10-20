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
from pathlib import Path
from streamlit_folium import st_folium


st.set_page_config(page_title="QalaGo · Астана", page_icon="Q", layout="wide", initial_sidebar_state="collapsed")


def load_optional_credentials() -> None:
    """Local/Cloud credentials stay in process memory, outside cached UI state."""
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
    for name in ("GROQ_API_KEY", "GROQ_MODEL", "OVERPASS_URL", "WEATHER_ENABLED"):
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
            st.markdown("Фотографии: [Vyacheslav Bukharov](https://commons.wikimedia.org/wiki/File:Astana-2021-10_-_18.jpg) · [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); [Ken and Nyetta](https://commons.wikimedia.org/wiki/File:View_from_Bayterek_tower.jpg) · [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/). Показаны с кадрированием и плавной прозрачностью.")
            st.link_button("Источник и лицензия OSM", "https://www.openstreetmap.org/copyright")
            st.caption("Локация задаётся вручную. GPS не запрашивается. Координаты и запросы не сохраняются в базе.")
            st.caption("Подбор выполняет Groq: ему передаются пожелания и сведения о местах рядом. Резервный режим включается отдельно. Карта загружается из интернета.")


def render_weather(response: RecommendResponse, request: RecommendRequest) -> None:
    weather = response.weather
    local = datetime.fromisoformat(response.local_datetime) if response.local_datetime else local_now()
    clock_label = "Выбранное время" if response.time_is_simulated else "Астана"
    parts = []
    if weather.is_simulated:
        parts.append("Погода: учебный сценарий")
    elif weather.temperature is not None:
        parts.append(f"{weather.temperature:g} °C")
    else:
        parts.append("Погода недоступна")
    if weather.apparent_temperature is not None:
        parts.append(f"ощущается {weather.apparent_temperature:g} °C")
    if weather.wind_speed is not None:
        parts.append(f"ветер {weather.wind_speed:g} м/с")
    st.markdown(
        f'<div class="conditions-bar"><div><span>{escape(clock_label)}</span>'
        f'<strong>{local:%H:%M}<small>{local:%d.%m.%Y}</small></strong></div>'
        f'<div><span>Погода</span><strong>{escape(" · ".join(parts))}</strong></div></div>',
        unsafe_allow_html=True,
    )
    if weather.status in {"caution", "severe"}:
        st.warning("Неблагоприятная погода. " + (
            "При подборе предпочтение отдаётся помещениям." if request.climate_shield_enabled
            else "Учёт погоды выключен в дополнительных условиях."))
    if request.time_mode == "simulated" and request.weather_mode == "live":
        st.caption("Выбранное время и текущая погода относятся к разным моментам.")


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
    st.caption("Маркеры обозначают приблизительное расположение мест. Для зданий это может быть центр, а не вход.")


def render_results(response: RecommendResponse, request: RecommendRequest, fingerprint: str) -> None:
    if response.general_message:
        st.info(response.general_message)
    if response.answer_mode == "ai_error":
        return
    if not response.recommendations:
        st.error("Мест не найдено по заданным параметрам.")
        st.caption("Увеличьте время, измените точку старта или условия поиска.")
    else:
        sort_column, _ = st.columns([1, 1])
        with sort_column:
            order = st.selectbox("Сортировка", options=list(SORT_OPTIONS),
                                format_func=SORT_OPTIONS.get, key="result_sort")
        response = replace(response, recommendations=sort_results(response.recommendations, order))
        with st.expander("Посмотреть на карте"):
            render_map(response, request, fingerprint)
        page_key = f"visible_{fingerprint}"
        visible = st.session_state.get(page_key, 6)
        cards = []
        for index, item in enumerate(response.recommendations[:visible], 1):
            closed = item.opening_status in {"closed", "closes_during_visit"}
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
            hours_text = format_hours(item.opening_hours) if item.opening_hours and item.opening_hours.strip() else "Информация о расписании отсутствует"
            if not item.opening_hours or not item.opening_hours.strip():
                status_label = "Часы работы"
                tone = "unknown"
            arrival_note = ('<p class="place-note">По расписанию откроется к вашему приходу; времени на посещение хватит.</p>'
                            if now_status == "closed" and item.opening_status == "open" else "")
            description = f'<p class="place-description">{escape(item.description)}</p>' if item.description else ""
            cards.append(
                '<article class="place-card">'
                f'<span class="place-category">{escape(CATEGORY_LABELS.get(item.category, item.category))}</span>'
                f'<h3>{index}. {escape(item.name)}</h3>'
                f'<p class="place-travel"><strong>≈ {item.travel_minutes_estimated:.0f} мин пешком</strong> · всего ≈ {item.total_minutes_estimated:.0f} мин</p>'
                f'{description}<p class="place-reason">{escape(item.reason)}</p>'
                '<div class="place-footer">'
                f'<div class="hours-panel {tone}"><strong>{escape(status_label)}</strong><div class="hours-text">{escape(hours_text)}</div></div>'
                f'{arrival_note}<a class="place-map-link" href="{escape(get_2gis_search_url(item.name), quote=True)}" '
                'target="_blank" rel="noopener noreferrer">Найти в 2ГИС</a></div></article>'
            )
        st.html('<div class="places-grid">' + ''.join(cards) + '</div>')
        if visible < len(response.recommendations):
            st.caption(f"Показано {visible} из {len(response.recommendations)}")
        if visible < len(response.recommendations):
            def show_more():
                st.session_state[page_key] = visible + 6
            st.button("Показать ещё места", on_click=show_more, key=f"more_{fingerprint}", use_container_width=True)
    with st.expander("Как рассчитаны время и доступность"):
        st.caption("Часы и расстояния могут отличаться от фактических. Перед выходом проверьте место в справочнике.")
        for limitation in response.limitations:
            st.caption(f"• {limitation}")


@st.fragment(run_every=60)
def render_current_results(fingerprint: str, current_request: RecommendRequest, conditions) -> None:
    stored = st.session_state.get("qalago_result")
    from core.geo import resolve_origin
    from core.weather import get_weather
    if stored and stored[0] == fingerprint:
        summary = stored[1]
        if current_request.time_mode == "live":
            summary = replace(summary, local_datetime=local_now().isoformat(),
                weather=get_weather(current_request.weather_mode, *resolve_origin(current_request)))
    else:
        from core.recommend import _request_time
        origin = resolve_origin(current_request)
        summary = RecommendResponse(weather=get_weather(current_request.weather_mode, *origin),
            local_datetime=_request_time(current_request).isoformat(),
            time_is_simulated=current_request.time_mode == "simulated")
    conditions.empty()
    with conditions.container():
        render_weather(summary, current_request)
    if stored and stored[0] == fingerprint:
        _, response, request = stored
        if request.time_mode == "live":
            calculated = datetime.fromisoformat(response.local_datetime) if response.local_datetime else None
            if calculated is not None and calculated.replace(second=0, microsecond=0) != local_now().replace(second=0, microsecond=0):
                try:
                    # Refresh availability for the same AI-selected places without replacing
                    # the AI answer or issuing a paid request every minute.
                    refreshed = []
                    for item in response.recommendations:
                        from core.hours import visit_status
                        from datetime import timedelta
                        now = local_now()
                        arrival = now + timedelta(minutes=item.travel_minutes_estimated)
                        status = visit_status(item.opening_hours, arrival, item.visit_minutes_estimated)
                        if request.require_open_hours and status != "open":
                            continue
                        if response.answer_mode == "llm" and status in {"closed", "closes_during_visit"}:
                            continue
                        refreshed.append(replace(item, opening_status=status,
                            opening_status_now=visit_status(item.opening_hours, now, 0),
                            arrival_datetime=arrival.isoformat()))
                    response = replace(response, recommendations=refreshed, local_datetime=local_now().isoformat())
                    st.session_state["qalago_result"] = (fingerprint, response, request)
                except Exception:
                    st.error("Не удалось обновить результаты по текущему времени. Повторите подбор.")
                    return
        render_results(response, request, fingerprint)
    elif stored:
        st.info("Условия изменились. Нажмите «Подобрать прогулку», чтобы пересчитать варианты.")


def main() -> None:
    st.markdown("""<style>
    :root {
      --eco-green: #28734f;
      --eco-dark: #205b40;
      --eco-mist: #edf5ee;
      --eco-border: #ccdfd0;
    }
    .stApp {
      background-color: #f1f5ef;
      background-image:
        linear-gradient(to right, transparent calc(50% - 560px), #f7faf6 calc(50% - 560px),
          #f7faf6 calc(50% + 560px), transparent calc(50% + 560px)),
        linear-gradient(to bottom, rgba(241,245,239,.65), #f1f5ef 1000px),
        url("https://upload.wikimedia.org/wikipedia/commons/c/c8/Astana-2021-10_-_18.jpg"),
        url("https://upload.wikimedia.org/wikipedia/commons/1/1d/View_from_Bayterek_tower.jpg");
      background-size: 100% 100%, 100% 1100px, 50% 1100px, 50% 1100px;
      background-position: center, center top, left top, right top;
      background-repeat: no-repeat;
    }
    .st-key-search_panel { background: linear-gradient(135deg, #ffffff, #f0f6f0);
      border: 1px solid var(--eco-border) !important;
      border-radius: 18px; box-shadow: 0 8px 28px rgba(40, 88, 58, .04); }
    .st-key-search_panel [data-testid="stWidgetLabel"] { color: #274d38; }
    [data-testid="stTextArea"] textarea:focus {
      border-color: var(--eco-green); box-shadow: 0 0 0 3px rgba(40,115,79,.12); }
    [data-testid="stBaseButton-primary"] { background: var(--eco-green); border-color: var(--eco-green);
      border-radius: 12px; min-height: 48px; box-shadow: 0 5px 14px rgba(40,115,79,.16); }
    [data-testid="stBaseButton-primary"]:hover { background: var(--eco-dark); border-color: var(--eco-dark); }
    [data-testid="stBaseButton-primary"]:focus-visible { outline: 3px solid #90b99b; outline-offset: 3px; }
    .place-category { display: inline-block; color: #637068;
      font-size: .77rem; letter-spacing: .035em; margin: 0 0 5px; }
    .place-reason { color: #35483e; background: transparent; border: 0;
      padding: 0; margin: 10px 0 4px; font-size: .94rem; line-height: 1.65; }
    [data-testid="stSidebar"] { background: #edf2eb; }

    [data-testid="stHeader"] { background-color: #f7faf6; }
    [data-testid="stMainBlockContainer"] { max-width: 1120px; padding-top: 6rem; padding-bottom: 3rem; }
    .conditions-bar { display: flex; align-items: center; gap: 32px;
      padding: 13px 18px; margin: 4px 0 22px; border: 1px solid #dde5d9;
      border-radius: 12px; background: rgba(255,254,251,.88); }
    .conditions-bar > div { display: flex; flex-direction: column; gap: 4px; }
    .conditions-bar span { color: #667366; font-size: .8rem; }
    .conditions-bar strong { color: #304b38; font-size: .96rem; font-weight: 500; }
    .conditions-bar small { font-size: .85rem; color: #667366; margin-left: 12px; }
    @media (max-width: 640px) { .conditions-bar { align-items: start; gap: 14px; flex-direction: column; } }
    @media (max-width: 1150px) { .stApp { background: #f7faf6; } }
    h1, h2, h3 { color: #173c3d; }
    h1 { font-size: 2.5rem; letter-spacing: -.04em; }
    [data-testid="stMetricValue"] { font-size: 1.35rem; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 16px; }
    .places-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
      grid-auto-rows: 1fr; gap: 20px; margin: 4px 0 12px; }
    .place-card { display: flex; flex-direction: column; min-width: 0; padding: 20px;
      overflow-wrap: anywhere; background: #fffefb; border-radius: 16px;
      border: 1px solid #dce2d9 !important; box-shadow: 0 3px 14px rgba(40,55,38,.035); }
    .place-card h3 { font-size: 1.35rem; line-height: 1.3; padding: 0; margin: 0 0 12px; }
    .place-travel { margin: 0 0 16px; }
    .place-footer { margin-top: auto; padding-top: 4px; }
    .place-card .place-map-link { display: block; text-align: center; margin-top: 12px;
      padding: 8px 12px; color: #35483e; background: transparent; border: 1px solid #d5ddd2;
      border-radius: 9px; text-decoration: none; }
    .place-card .place-map-link:hover { background: #f1f5ef; }
    .place-card .place-map-link:focus-visible { outline: 3px solid #90b99b; outline-offset: 3px; }
    .place-note { color: #687269; font-size: .82rem; margin: 6px 0 0; }
    .hours-panel { padding: 12px 0 8px; margin: 10px 0 0; font-size: .81rem;
      border-top: 1px solid #e4e8e0; }
    .hours-panel strong { font-weight: 500; }
    .hours-panel.open { color: #39624a; }
    .hours-panel.open strong { display: inline-block; color: var(--eco-dark);
      background: var(--eco-mist); border-radius: 7px; padding: 5px 9px; font-weight: 600; }
    .hours-panel.closed { color: #90633d; }
    .hours-panel.unknown { color: #687269; }
    .hours-text { margin-top: 5px; color: #687269; font-size: .82rem; line-height: 1.55; white-space: pre-line; }
    .place-description { color: #526665; font-size: .95rem; line-height: 1.5; margin: 0 0 4px; }
    @media (max-width: 640px) {
      .places-grid { grid-template-columns: minmax(0, 1fr); gap: 14px; }
      .place-card { padding: 16px; }
      [data-testid="stMainBlockContainer"] { padding-top: 5rem; }
      h1 { font-size: 2rem; }
    }
    </style>""", unsafe_allow_html=True)
    stats = snapshot_stats()
    render_sidebar(stats)
    st.title("Куда пойти в свободное время?")
    conditions = st.empty()

    with st.container(border=True, key="search_panel"):
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
            selected_interests = st.multiselect("Что интересно?", list(INTERESTS), default=[],
                                               placeholder="Например, кофе или музеи")
        query = st.text_area("Какое место вы ищете?", placeholder="Например: спокойная кофейня на 30 минут после работы, средний чек до 3000 ₸", max_chars=1000, height=100)
        company_column, language_column = st.columns(2)
        with company_column:
            group_size = st.selectbox("Сколько вас?", [1, 2, 3, 4, 5],
                                      format_func=lambda size: "Один человек" if size == 1 else f"Компания · {size} чел.",
                                      key="group_size")
        with language_column:
            languages = {"auto": "По языку запроса", "ru": "Русский", "kk": "Қазақша", "en": "English"}
            language = st.selectbox("Язык описаний", list(languages), format_func=languages.get, key="answer_language")
        member_preferences = []
        if group_size > 1:
            with st.expander("Пожелания участников", expanded=True):
                st.caption("Обязательные условия укажите в общем запросе. Здесь — интересы для поиска компромисса.")
                for member in range(group_size):
                    member_preferences.append(st.text_input(
                        f"Участник {member + 1}", placeholder="Например: кофе, прогулка или архитектура",
                        max_chars=300, key=f"member_preference_{member}"))
                st.caption("Наличие мест для всей компании нужно уточнить у заведения.")
        with st.expander("Дополнительные условия"):
            require_open_hours = st.checkbox("Только открытые по расписанию", key="require_open_hours",
                help="Исключает места с неизвестным расписанием и те, что закроются до конца посещения. Это расчёт по часам работы, а не проверка на месте.")
            allow_fallback = st.checkbox("Разрешить резервный режим без ИИ (не рекомендуется)", value=False)
            outlets = st.checkbox("Обязательно подтверждённая розетка", key="require_outlets", help="Неизвестное наличие розеток не считается подтверждением. Результат может быть пустым.")
            return_trip = st.checkbox("Вернуться к точке старта", key="return_trip")
            flight = st.checkbox("Время ограничено вылетом", key="flight_constraint", help="Для аэропорта действует консервативное ограничение: без поездки в центр. Это не расчёт времени посадки и досмотра.")
            st.divider()
            shield = st.toggle("Учитывать плохую погоду", value=True, help="При ветре, дожде и морозе отдаём предпочтение помещениям. Защита от погоды не гарантируется.")
            weather_label = st.selectbox("Погода", list(WEATHER_MODES), index=4)
            weather_mode = WEATHER_MODES[weather_label]
            if weather_mode != "live":
                st.info("СИМУЛЯЦИЯ ПОГОДЫ · учебный сценарий, не текущая погода и не прогноз.")
            time_label = st.radio("Когда пойдём? · время Астаны", ["Сейчас", "Симуляция"], horizontal=True, key="time_choice")
            time_mode = "live" if time_label == "Сейчас" else "simulated"
            simulated_datetime = None
            if time_mode == "simulated":
                now = datetime.now(TIMEZONE)
                date_col, time_col = st.columns(2)
                chosen_date = date_col.date_input("Дата сценария", value=now.date())
                chosen_time = time_col.time_input("Время сценария", value=now.replace(hour=22, minute=0, second=0, microsecond=0).time())
                simulated_datetime = datetime.combine(chosen_date, chosen_time).replace(tzinfo=TIMEZONE).isoformat()
                st.caption("СИМУЛЯЦИЯ ВРЕМЕНИ · доступность рассчитана по расписанию на выбранный момент.")
            if time_mode == "simulated" and weather_mode == "live":
                st.warning("Выбраны часы сценария и погода текущего момента.")


    interests = [INTERESTS[label] for label in selected_interests]
    if outlets:
        interests.append("power_outlets")
    request = RecommendRequest(
        location_preset=preset, latitude=latitude, longitude=longitude,
        query=query, interests=interests, duration_minutes=duration,
        return_to_start=return_trip, climate_shield_enabled=shield,
        weather_mode=weather_mode, time_mode=time_mode,
        simulated_datetime=simulated_datetime, flight_constraint=flight, allow_fallback=allow_fallback,
        group_size=group_size, member_preferences=member_preferences, language=language,
        require_open_hours=require_open_hours,
    )
    # A changed control invalidates displayed results. Never reuse a previous
    # response as if it belonged to the new origin/weather/time/constraints.
    fingerprint = hashlib.sha256(json.dumps(asdict(request), sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    data_ready = "error" not in stats and stats.get("count", 0) > 0
    if not data_ready:
        st.warning("База мест недоступна. Для восстановления выполните команду ниже в папке проекта.")
        st.code("python -m ingestion.build_database", language="bash")
    if st.button("Подобрать прогулку", type="primary", use_container_width=True, disabled=not data_ready):
        try:
            with st.spinner("ИИ изучает пожелания и выбирает места рядом…"):
                response = recommend(request, db_path=DB_PATH)
            st.session_state[f"visible_{fingerprint}"] = 6
            st.session_state["qalago_result"] = (fingerprint, response, request)
        except Exception:
            st.session_state.pop("qalago_result", None)
            st.error("Подбор сейчас недоступен. Проверьте локальный снимок командой python -m ingestion.build_database --offline и повторите попытку.")
    render_current_results(fingerprint, request, conditions)


if __name__ == "__main__":
    main()
