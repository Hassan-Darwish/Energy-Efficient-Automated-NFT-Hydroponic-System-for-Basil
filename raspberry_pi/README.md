# Raspberry Pi software

The Raspberry Pi logs data, shows a simple dashboard, and later chooses dose requests. It does not drive pumps.

## Run the USB serial dashboard

The ESP32-S3 sends one JSON frame about every 2 seconds. This folder reads that frame, checks it, logs it, and draws it. Set `SERIAL_PORT` in `config.py` to the port that appears when the board is plugged in.

From this folder:

```text
pip install -r requirements.txt
streamlit run dashboard.py
```

Accepted frames are appended to `data/sensor_log.csv`. A bad line or a missing board is appended to `data/serial_errors.csv` and the page stays open. The only command sent in this milestone is `no_action`.

Dosing methods below are still planned for later milestones.

## Role

- Read JSON telemetry from the ESP32-S3 over USB serial.
- Append sensor rows to a CSV log.
- Show the latest readings on a simple dashboard.
- When dosing is enabled, choose a dose with one method and send a `dose_request`.
- Record the ESP32-S3 `dose_result`, including rejected requests.

If the ESP32-S3 rejects a request, the Pi logs the reason and waits. It does not retry in a tight loop, and it has no path that bypasses the ESP32-S3.

## Planned files

| File | Purpose |
| --- | --- |
| `main.py` | Read one frame, log it, and send the monitoring command |
| `serial_reader.py` | Timeout-based USB serial read and write of one JSON line |
| `dashboard.py` | Streamlit view of the latest frame and the CSV history |
| `data_logger.py` | Append frames to `data/sensor_log.csv` and errors to `data/serial_errors.csv` |
| `config.py` | Serial port, baud rate, CSV path, and required JSON fields |
| `data/sensor_log.csv` | Created when logging starts |
| `data/dosing_dataset.csv` | Created when dose requests are logged; later used if ANFIS is trained |

## Dosing methods

All methods live under `dosing_methods/` and share one interface: given the latest telemetry, return a dose request or no request. The ESP32-S3 still decides whether the pump runs.

| File | Method | When it is used |
| --- | --- | --- |
| `dosing_methods/base.py` | Shared request shape | Every method |
| `dosing_methods/fixed_rules.py` | Threshold rules for pH and EC | First dosing milestone |
| `dosing_methods/pid_control.py` | PID on pH or EC error | Optional, after fixed rules |
| `dosing_methods/fuzzy_logic.py` | Fuzzy dose size from error and rate of change | Optional |
| `dosing_methods/anfis_model.py` | ANFIS dose from logged examples | Optional, after a dataset exists |

ANFIS is not required for the system to grow basil. Fixed rules plus ESP32-S3 safety are the core.

## Related documents

- [../docs/system_architecture.md](../docs/system_architecture.md)
- [../docs/communication_protocol.md](../docs/communication_protocol.md)
- [../docs/milestones.md](../docs/milestones.md)
- [../docs/testing_plan.md](../docs/testing_plan.md)
