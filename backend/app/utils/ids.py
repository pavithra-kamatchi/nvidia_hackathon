import uuid
from datetime import datetime


def generate_id(prefix: str, timestamp: datetime) -> str:
    """Timestamp-prefixed id so a record's creation time is visible from its
    id alone (per the requirement that every record be identifiable by the
    timestamp of the notification that produced it)."""
    stamp = timestamp.strftime("%Y%m%dT%H%M%S%f")
    return f"{prefix}_{stamp}_{uuid.uuid4().hex[:6]}"
