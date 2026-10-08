"""Poll the ESP32 once, log a good frame, and send the monitoring command."""

from datetime import datetime

import config
from data_logger import append_reading, log_error
from serial_reader import SerialLink


def message_to_row(message):
    """Copy the frame and stamp it with the time the Pi accepted it."""
    row = {column: message.get(column) for column in config.COLUMNS if column != "timestamp"}
    row["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return row


def poll_once(link: SerialLink):
    """Read one line. Timeout, bad JSON, and a missing board all return normally."""
    try:
        message, error = link.read_message()
    except Exception as exc:
        log_error(str(exc))
        return {"reading": None, "error": str(exc), "connected": False}

    if error == "disconnected":
        shown = f"ESP32 is not connected on {config.SERIAL_PORT}"
        logged = link.disconnect_message_once()
        if logged:
            log_error(logged)
        return {"reading": None, "error": shown, "connected": False}

    if error:
        log_error(error)
        return {"reading": None, "error": error, "connected": link.is_open()}

    if message is None:
        return {"reading": None, "error": None, "connected": link.is_open()}

    row = message_to_row(message)
    try:
        append_reading(row)
    except Exception as exc:
        text = f"CSV log failed: {exc}"
        log_error(text)
        return {"reading": row, "error": text, "connected": True}

    try:
        link.send_monitoring_command()
    except Exception as exc:
        text = f"command not sent: {exc}"
        log_error(text)
        return {"reading": row, "error": text, "connected": link.is_open()}

    return {"reading": row, "error": None, "connected": True}
