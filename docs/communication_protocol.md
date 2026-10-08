# Communication protocol

The ESP32-S3 and the Raspberry Pi talk over USB serial. Messages are JSON text, UTF-8, one object per line. Each line ends with a newline character (`\n`).

The ESP32-S3 never treats a Pi message as a raw pin command. The only action a Pi message can request is a timed pump pulse, and safety rules may reject it.

## Link settings

| Setting | Value |
| --- | --- |
| Physical link | USB serial |
| Encoding | UTF-8 |
| Framing | One JSON object per line |
| Baud rate | 115200 |
| Direction | ESP32-S3 sends telemetry and dose results. Raspberry Pi sends dose requests. |

Use a baud rate of 115200 on both ends. If a line is longer than 512 bytes, or it is not valid JSON, the receiver discards that line and waits for the next newline.

Unknown fields are ignored. Unknown `type` values are rejected. Unknown `pump` names are rejected.

## Message types

| `type` | Sender | Purpose |
| --- | --- | --- |
| `telemetry` | ESP32-S3 | Latest sensor values, pump states, and safety faults |
| `dose_request` | Raspberry Pi | Ask the ESP32-S3 to run one pump for a limited time |
| `dose_result` | ESP32-S3 | Accept or reject that request |

The ESP32-S3 sends telemetry about once per second. It sends a `dose_result` as soon as it accepts or rejects a request. It does not wait for the pump to finish before sending the result. Pump state in later telemetry shows whether the pulse is still on.

## Telemetry

Example:

```json
{"type":"telemetry","ts_ms":123456,"ph":6.2,"ec":1.4,"water_temp_c":22.5,"air_temp_c":24.0,"air_humidity":55.0,"light_lux":null,"level_ok":true,"flow_lpm":2.1,"pumps":{"solution_a":false,"solution_b":false,"ph_up":false,"ph_down":false,"fresh_water":false,"circulation":true},"safety":{"ok":true,"faults":[]}}
```

| Field | Meaning |
| --- | --- |
| `type` | Always `telemetry` |
| `ts_ms` | Milliseconds since the ESP32-S3 started |
| `ph` | pH, or `null` if invalid |
| `ec` | EC in mS/cm, or `null` if invalid |
| `water_temp_c` | Water temperature in °C, or `null` if invalid |
| `air_temp_c` | Air temperature in °C, or `null` if invalid |
| `air_humidity` | Relative humidity in percent, or `null` if invalid |
| `light_lux` | Lux from the BH1750, or `null` if the sensor is absent or invalid |
| `level_ok` | `true` when the tank is at or above the minimum mark |
| `flow_lpm` | Flow in litres per minute, or `null` if invalid |
| `pumps` | `true` while that pump output is on |
| `safety.ok` | `true` when `faults` is empty |
| `safety.faults` | List of active fault strings. Empty when the system is clear. |

Fault strings use the same words as dose rejection reasons when they describe the same problem: `level_low`, `sensor_invalid`, `circulation_off`, `tank_full`. A fault can be active even when no dose was requested. For example, a low level raises `level_low` in `safety.faults` on the next telemetry line.

Numeric sensor fields are JSON numbers. Invalid or unwired optional values are `null`, not `0`. A real pH of 0 is outside the valid range and is also sent as `null` with `sensor_invalid` in `safety.faults`.

## Dose request

The Raspberry Pi sends this only when a dosing method wants a pulse:

```json
{"type":"dose_request","id":42,"pump":"solution_a","duration_ms":1500}
```

| Field | Meaning |
| --- | --- |
| `type` | Always `dose_request` |
| `id` | Integer chosen by the Pi. The ESP32-S3 copies it into the result. |
| `pump` | One of `solution_a`, `solution_b`, `ph_up`, `ph_down`, `fresh_water` |
| `duration_ms` | Requested on-time in milliseconds, from 1 up to the maximum in [safety_rules.md](safety_rules.md) |

`circulation` is not accepted in `dose_request`. The ESP32-S3 turns the circulation pump on and off from level and flow. A request that names `circulation` is rejected with `unknown_pump`.

One request names one pump. To dose Solution A and then Solution B, the Pi sends two requests, and it waits for the first result plus the gap that the ESP32-S3 enforces.

The Pi chooses `id` values that increase by one for each new request. Reusing an `id` that was already answered is rejected with `bad_message`.

## Dose result

```json
{"type":"dose_result","id":42,"accepted":true,"reason":"ok"}
```

Rejected example:

```json
{"type":"dose_result","id":42,"accepted":false,"reason":"level_low"}
```

| Field | Meaning |
| --- | --- |
| `type` | Always `dose_result` |
| `id` | Same integer as the request |
| `accepted` | `true` only if the pump was started |
| `reason` | Short machine-readable string from the table below |

| `reason` | When it is used |
| --- | --- |
| `ok` | The pump was started and the stop deadline is armed |
| `level_low` | Tank level is below the minimum |
| `tank_full` | Fresh-water dose would overflow the tank |
| `sensor_invalid` | A sensor required for this dose is invalid |
| `duration_too_long` | `duration_ms` is above the maximum for that pump, or below 1 |
| `pump_conflict` | Another dosing pump is on, or the A/B or pH gap has not finished |
| `circulation_off` | Circulation is off or flow is not valid |
| `pump_not_fitted` | The named pump is optional and not installed (`fresh_water` until it is fitted) |
| `unknown_pump` | The `pump` string is not a dosing pump name |
| `bad_message` | JSON type is wrong, `id` is missing or reused, or `duration_ms` is missing or not a number |

`accepted` is `true` only together with `reason` `ok`.

## What is deliberately absent

- No message sets a GPIO number.
- No message clears faults or disables a safety rule.
- No message changes the maximum dose time.
- No field such as `force` or `override` is defined. If a sender adds one, the ESP32-S3 ignores that field and still applies the safety rules.

## Pi behavior

- Parse each line on its own. A bad line is logged and skipped.
- Log every `telemetry` object and every `dose_result`.
- After a rejection, wait at least 5 seconds before sending another request, and send a new `id`.
- If the serial port disappears, reconnect and keep logging. Do not assume a dose finished unless a later telemetry line shows that pump as `false`.
