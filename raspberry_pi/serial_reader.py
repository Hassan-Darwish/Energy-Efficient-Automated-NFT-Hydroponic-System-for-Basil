"""Read and write one JSON line on the ESP32 USB serial port.

A missing board, a timeout, or a bad line returns a result. It does not raise
into the dashboard.
"""

import json

import serial

import config


def _whole_number(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and value.is_integer()


def validate_message(message):
    """Return an error string, or None when the frame has the expected fields."""
    if not isinstance(message, dict):
        return "invalid JSON: expected an object"
    for field in config.REQUIRED_FIELDS:
        if field not in message:
            return f"invalid JSON: missing {field}"
    if not _whole_number(message["sequence"]):
        return "invalid JSON: sequence is not an integer"
    for field in config.NUMERIC_FIELDS:
        value = message[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"invalid JSON: {field} is not a number"
    for field in ("protocol_version", "device_id", "system_status"):
        value = message[field]
        if not isinstance(value, str) or value == "":
            return f"invalid JSON: {field} is not text"
    if message["system_status"] not in config.STATUS_VALUES:
        return "invalid JSON: system_status is not recognised"
    return None


class SerialLink:
    """One open port, with a short timeout so the dashboard can keep refreshing."""

    def __init__(self):
        self._port = None
        self._pending = b""
        self._disconnect_logged = False

    def is_open(self):
        return self._port is not None and self._port.is_open

    def ensure_open(self):
        if self.is_open():
            return True
        try:
            self._port = serial.Serial(
                config.SERIAL_PORT,
                config.BAUD_RATE,
                timeout=config.SERIAL_TIMEOUT,
                write_timeout=config.SERIAL_TIMEOUT,
            )
        except serial.SerialException:
            self._port = None
            return False
        self._pending = b""
        self._disconnect_logged = False
        return True

    def close(self):
        if self._port is not None:
            try:
                self._port.close()
            except serial.SerialException:
                pass
        self._port = None

    def disconnect_message_once(self):
        """Log text the first time the port is missing, then stay quiet."""
        message = f"ESP32 is not connected on {config.SERIAL_PORT}"
        if self._disconnect_logged:
            return None
        self._disconnect_logged = True
        return message

    def read_message(self):
        """Return (message, error). A timeout is (None, None)."""
        if not self.ensure_open():
            return None, "disconnected"
        try:
            raw = self._port.readline()
        except serial.SerialException:
            self.close()
            return None, "disconnected"
        if not raw:
            return None, None
        if not raw.endswith(b"\n"):
            self._pending += raw
            if len(self._pending) > config.MAX_LINE_BYTES:
                self._pending = b""
                return None, "invalid JSON: line too long"
            return None, None

        line_bytes = self._pending + raw
        self._pending = b""
        text = line_bytes.decode("utf-8", errors="replace").strip()
        if text == "":
            return None, None
        try:
            message = json.loads(text)
        except json.JSONDecodeError:
            preview = text[:120]
            return None, f"invalid JSON: {preview}"
        problem = validate_message(message)
        if problem:
            return None, problem
        return message, None

    def send_monitoring_command(self):
        """Ask for nothing. This only proves the Pi can write a command line."""
        if not self.is_open():
            return
        line = json.dumps(config.MONITOR_COMMAND) + "\n"
        try:
            self._port.write(line.encode("utf-8"))
        except serial.SerialException:
            self.close()
            raise
