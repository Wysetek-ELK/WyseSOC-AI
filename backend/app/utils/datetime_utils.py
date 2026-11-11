from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return a timezone-naive UTC datetime without invoking deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_from_timestamp(timestamp_seconds: float) -> datetime:
    """Return a timezone-naive UTC datetime from POSIX seconds without utcfromtimestamp()."""
    return datetime.fromtimestamp(float(timestamp_seconds), tz=timezone.utc).replace(tzinfo=None)

