"""Serial link settings and the columns stored from each ESP32 frame.

Change SERIAL_PORT to the port that appears when the ESP32-S3 is plugged in.
Windows usually shows COM3, COM4, and so on. The Pi usually shows /dev/ttyACM0.
"""

import sys
from pathlib import Path

# Timeout-based reads. The ESP32 sends one frame about every 2 seconds.
SERIAL_TIMEOUT = 1.0
BAUD_RATE = 115200
if sys.platform.startswith("win"):
    SERIAL_PORT = "COM5"
else:
    SERIAL_PORT = "/dev/ttyACM0"

# Drop a partial line that never reaches a newline.
MAX_LINE_BYTES = 512

HISTORY_ROWS = 60

CSV_PATH = Path(__file__).resolve().parent / "data" / "sensor_log.csv"
ERROR_LOG_PATH = Path(__file__).resolve().parent / "data" / "serial_errors.csv"

# Pi adds timestamp. The other columns are copied from the ESP32 JSON frame.
COLUMNS = [
    "timestamp",
    "protocol_version",
    "device_id",
    "sequence",
    "ph",
    "ec_tds",
    "water_level",
    "water_temperature",
    "flow_rate",
    "air_temperature",
    "humidity",
    "light_intensity",
    "system_status",
]

CHART_COLUMNS = [
    "ph",
    "ec_tds",
    "water_level",
    "water_temperature",
    "flow_rate",
    "air_temperature",
    "humidity",
    "light_intensity",
]

REQUIRED_FIELDS = [
    "protocol_version",
    "device_id",
    "sequence",
    "ph",
    "ec_tds",
    "water_level",
    "water_temperature",
    "flow_rate",
    "air_temperature",
    "humidity",
    "light_intensity",
    "system_status",
]

NUMERIC_FIELDS = [
    "ph",
    "ec_tds",
    "water_level",
    "water_temperature",
    "flow_rate",
    "air_temperature",
    "humidity",
    "light_intensity",
]

STATUS_VALUES = ("NORMAL", "WARNING", "ALARM")

# This milestone only sends the monitoring command. The other names are the
# actions the ESP32 already accepts and stores.
MONITOR_COMMAND = {
    "action": "no_action",
    "duration_seconds": 0,
    "reason": "monitoring_only",
}
