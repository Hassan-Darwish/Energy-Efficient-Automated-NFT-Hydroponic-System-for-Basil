# Testing plan

Test each milestone before starting the next one. Early tests use water, beakers, and a serial terminal. Nutrient concentrates and pH chemicals stay out of the pumps until milestone 7 has passed with water.

Record the date, the milestone, and pass or fail for each row in a lab notebook or a short test sheet. A failed row is fixed and repeated before the milestone is marked done.

## Equipment

- ESP32-S3 and the Raspberry Pi, with a USB serial cable
- ADS1115, pH probe, EC probe, DS18B20, flow sensor, level sensor, and one air sensor (BME280 or AHT20)
- Pump driver boards and the dosing pumps
- Multimeter
- pH buffer solutions (pH 4 and pH 7) and an EC calibration standard
- A serial terminal on a PC (milestones 2–4) and the Pi programs (milestones 5–8)
- Optional: BH1750, fresh-water pump, backup valves

## Milestone 2 — Sensors

| Check | Pass condition |
| --- | --- |
| pH 7 buffer | Reading within about 0.1 of 7.0 after calibration |
| pH 4 buffer | Reading within about 0.1 of 4.0 after calibration |
| EC standard | Reading close to the standard at the measured water temperature |
| DS18B20 | Temperature moves when the probe is warmed by hand and returns toward room temperature |
| Level | Output changes when the sensor is above and below the minimum mark |
| Flow | Pulses or litres per minute rise only while water is moving |
| Air sensor | Temperature and humidity values appear and match a room check |
| Unplugged pH probe | Value is reported invalid, not as a usable number |
| BH1750, if fitted | Lux drops when the sensor is covered |

## Milestone 3 — Actuator pulses

Use water lines. Command pulses from a local test input or a temporary serial command that still goes through the deadline code.

| Check | Pass condition |
| --- | --- |
| Solution A, 1.5 s | Pump runs, then stops. Measured on-time is close to 1.5 s. |
| Solution B, pH Up, pH Down | Same start-and-stop behavior, each within its maximum |
| Duration above the maximum | Pump never turns on |
| USB unplugged during a 3 s pulse | Pump still turns off at the deadline |
| Circulation with level switch safe | Circulation turns on |
| Circulation with level switch low | Circulation stays off |

## Milestone 4 — Safety

Simulate faults with the real level switch, by unplugging a sensor, or with a test input that the safety module already treats as a sensor value. Do not add a bypass that skips these checks in the final firmware.

| Check | Pass condition |
| --- | --- |
| Level low during circulation | Circulation stops |
| Level low during a dose | Dosing pump stops immediately |
| Level restored for one sample only | Dosing stays blocked until the level has been safe for 5 seconds |
| pH probe unplugged | pH Up and pH Down requests are refused |
| EC probe unplugged | Solution A and Solution B requests are refused |
| Water temperature sensor unplugged | All dosing pumps stay off |
| Circulation off | A dose request is refused |
| Flow lost while circulation is commanded on | Circulation and dosing stop |
| Solution A and Solution B requested together | Second pump stays off |
| Solution B requested 2 seconds after Solution A | Refused. Allowed only after the 10 second gap |
| pH Up and pH Down requested together | Second pump stays off |
| Dose of 30 seconds | Refused for every dosing pump |

## Milestone 5 — Telemetry link

| Check | Pass condition |
| --- | --- |
| Normal telemetry | Pi prints one JSON object per second with the fields in [communication_protocol.md](communication_protocol.md) |
| Invalid pH | `ph` is `null` and `safety.faults` contains `sensor_invalid` |
| Corrupt line from a manual test | Pi skips the line and keeps reading the next good line |
| Cable unplugged | Pi reports the disconnect. ESP32-S3 pumps still obey milestone 3 and 4 |

## Milestone 6 — Log and dashboard

| Check | Pass condition |
| --- | --- |
| Run for 2 minutes | `sensor_log.csv` gains about one row per second |
| Dashboard | Shown pH, EC, temperatures, level, flow, and pump states match the newest CSV row |
| Empty or waiting state | Dashboard shows that no sample has arrived yet, without crashing, before the ESP32-S3 is connected |
| Stop the Pi program | ESP32-S3 circulation and safety behavior do not change |
| Restart the Pi program | Logging continues by appending rows. Earlier rows remain |

## Milestone 7 — Fixed rules

Set basil targets in `config.py` before the test (a typical starting point is pH 6.0 and EC 1.2 mS/cm; confirm the numbers with the project supervisor). Use water plus safe test solutions, or run the chemical test only after the supervisor agrees.

| Check | Pass condition |
| --- | --- |
| pH below target by more than the rule band | Pi sends `ph_up`. ESP32-S3 replies `accepted: true` and the pump stops by itself |
| pH above target by more than the rule band | Pi sends `ph_down` and the pump completes one pulse |
| EC below target | Pi sends `solution_a`, waits for the result and the gap, then sends `solution_b` |
| EC above target and fresh-water pump absent | Pi does not send `fresh_water`, or the ESP32-S3 replies `pump_not_fitted` |
| Low level while a rule wants a dose | Result reason is `level_low`. Pump stays off |
| Request longer than the maximum | Result reason is `duration_too_long` |
| Second dose during the gap | Result reason is `pump_conflict` |
| USB removed mid-pulse | Pump stops at the ESP32-S3 deadline. The dosing CSV does not show a second start for the same `id` |
| Dashboard left open | Refusals still appear in `dosing_dataset.csv` with `id`, pump, duration, `accepted`, and `reason` |

## Milestone 8 — Optional methods

Run this milestone only if PID, fuzzy logic, or ANFIS is in the project scope.

| Check | Pass condition |
| --- | --- |
| Method switch in `config.py` | The active method changes, and requests still use `dose_request` |
| PID or fuzzy pulse | Duration never exceeds the ESP32-S3 maximum |
| ANFIS before training data exists | The program keeps fixed rules active and explains that the dataset is too small |
| Unsafe ANFIS or PID request | ESP32-S3 rejects it with the same reasons as milestone 7 |

## Demonstration script for the final review

1. Power the ESP32-S3 with the Pi disconnected. Show circulation follow the level switch, and show a pump stop on its deadline.
2. Connect USB. Show telemetry on the dashboard and a new CSV row.
3. Move pH or EC out of band with a known test solution. Show one accepted dose and the matching `dose_result`.
4. Force a low level. Show a rejected request and both pumps off.
5. Unplug USB during a short water pulse. Show the pump stop without a further message from the Pi.
