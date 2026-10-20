"""One local clock for recommendations and live result expiry."""
from datetime import datetime

from config import TIMEZONE


def local_now() -> datetime:
    return datetime.now(TIMEZONE)
