"""Shared public configuration. No credentials or user locations are stored here."""
import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "pois.db"
TIMEZONE = ZoneInfo("Asia/Almaty")
# Approximate public landmarks, not user GPS. See docs/DATA_PROVENANCE.md.
PRESETS = {
    "expo": {"name": "EXPO / MEGA Silk Way", "lat": 51.0894, "lon": 71.4070},
    "baiterek": {"name": "Байтерек", "lat": 51.1282, "lon": 71.4304},
    "central_park": {"name": "Парк Астана / Центральный парк", "lat": 51.1548, "lon": 71.4196},
    "airport": {"name": "Аэропорт NQZ", "lat": 51.0280, "lon": 71.4635},
}
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
