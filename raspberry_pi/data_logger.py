"""Append ESP32 frames to the sensor CSV and keep serial errors in their own file."""

from datetime import datetime
from pathlib import Path

import pandas as pd

import config


def _header_matches(path: Path, columns) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    first = path.read_text(encoding="utf-8").splitlines()
    if not first:
        return False
    return first[0].strip() == ",".join(columns)


def _ensure_csv(path: Path, columns) -> None:
    """Create a header row. An older local-fake log is moved aside, not mixed in."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not _header_matches(path, columns):
        # The first dashboard log had no serial columns. Keep it, then start clean.
        if path.resolve() == config.CSV_PATH.resolve():
            backup = path.with_name("sensor_log_local_fake.csv")
        else:
            backup = path.with_name(path.stem + "_previous.csv")
        if backup.exists():
            backup.unlink()
        path.rename(backup)
    if not path.exists():
        pd.DataFrame(columns=columns).to_csv(path, index=False)


def append_reading(reading: dict) -> None:
    """Add one accepted frame. The header is written only when the file is created."""
    path = config.CSV_PATH
    _ensure_csv(path, config.COLUMNS)
    row = pd.DataFrame([{column: reading[column] for column in config.COLUMNS}])
    row.to_csv(path, mode="a", header=False, index=False)


def load_history(limit: int = config.HISTORY_ROWS) -> pd.DataFrame:
    """Return the newest rows, up to the chart window."""
    path = config.CSV_PATH
    _ensure_csv(path, config.COLUMNS)
    frame = pd.read_csv(path)
    if frame.empty:
        return frame
    return frame.tail(limit)


def log_error(message: str) -> None:
    """Record a bad line or a lost port. Failures here must not stop the dashboard."""
    path = config.ERROR_LOG_PATH
    try:
        _ensure_csv(path, ["timestamp", "message"])
        row = pd.DataFrame(
            [
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": message,
                }
            ]
        )
        row.to_csv(path, mode="a", header=False, index=False)
    except OSError:
        return
