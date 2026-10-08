"""Dashboard for JSON frames from the ESP32-S3.

Run from this folder: streamlit run dashboard.py
The serial read uses a timeout. The page keeps running when the board is
unplugged or a line is not valid JSON.
"""

import time

import streamlit as st

import config
from data_logger import load_history
from main import poll_once
from serial_reader import SerialLink

st.set_page_config(page_title="Hydroponic dashboard", layout="wide")
st.title("Hydroponic dashboard")
st.caption(
    f"USB serial on {config.SERIAL_PORT} at {config.BAUD_RATE} baud. "
    "The ESP32 sends fake readings until real sensors are connected."
)

if "serial_link" not in st.session_state:
    st.session_state.serial_link = SerialLink()
if "last_reading" not in st.session_state:
    st.session_state.last_reading = None

result = poll_once(st.session_state.serial_link)
if result["reading"] is not None:
    st.session_state.last_reading = result["reading"]

reading = st.session_state.last_reading

if not result["connected"]:
    st.warning(result["error"])
elif result["error"]:
    st.error(result["error"])
elif reading is None:
    st.info("Connected. Waiting for the first JSON frame.")
elif reading["system_status"] == "NORMAL":
    st.success(f"System {reading['system_status']}")
elif reading["system_status"] == "WARNING":
    st.warning(f"System {reading['system_status']}")
else:
    st.error(f"System {reading['system_status']}")

st.subheader("Current readings")

if reading is None:
    st.info("No frame received yet.")
else:
    sensor_cards = [
        ("pH", f"{float(reading['ph']):.1f}"),
        ("EC/TDS (ppm)", f"{float(reading['ec_tds']):.0f}"),
        ("Water level (%)", f"{float(reading['water_level']):.0f}"),
        ("Water temperature (°C)", f"{float(reading['water_temperature']):.1f}"),
        ("Flow rate (L/min)", f"{float(reading['flow_rate']):.1f}"),
        ("Air temperature (°C)", f"{float(reading['air_temperature']):.1f}"),
        ("Humidity (%)", f"{float(reading['humidity']):.0f}"),
        ("Light intensity (lux)", f"{float(reading['light_intensity']):.0f}"),
    ]
    first_row = st.columns(4)
    second_row = st.columns(4)
    for index, (label, value) in enumerate(sensor_cards):
        target = first_row if index < 4 else second_row
        target[index % 4].metric(label, value)

    status_row = st.columns(3)
    status_row[0].metric("System status", str(reading["system_status"]))
    status_row[1].metric("Device", str(reading["device_id"]))
    status_row[2].metric("Sequence", str(reading["sequence"]))

st.subheader("Sensor history")
history = load_history()
if history.empty:
    st.info("No rows in the log yet.")
else:
    # Separate charts so pH and EC are not drawn on one shared scale.
    left, right = st.columns(2)
    indexed = history.set_index("timestamp")
    for index, column in enumerate(config.CHART_COLUMNS):
        side = left if index % 2 == 0 else right
        side.line_chart(indexed[[column]])

# A missing port returns at once. Wait out the same timeout so the page does not spin.
if not result["connected"]:
    time.sleep(config.SERIAL_TIMEOUT)
st.rerun()
