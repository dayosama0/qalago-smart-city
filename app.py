"""QalaGo entrypoint: optional secrets, then the responsive Streamlit UI."""
import os

import streamlit as st
from dotenv import load_dotenv


st.set_page_config(page_title="QalaGo · Астана", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")


def load_optional_credentials() -> None:
    """Keep credentials in process memory, outside cached UI/session state."""
    load_dotenv(override=False)
    for name in ("OPENAI_API_KEY", "OPENAI_MODEL", "OVERPASS_URL", "WEATHER_ENABLED"):
        if os.environ.get(name):
            continue
        try:
            value = st.secrets.get(name)
        except Exception:
            # Missing optional secrets never stop the deterministic no-key app.
            value = None
        if isinstance(value, str) and value:
            os.environ[name] = value


load_optional_credentials()

from ui.interface import main  # noqa: E402


if __name__ == "__main__":
    main()
