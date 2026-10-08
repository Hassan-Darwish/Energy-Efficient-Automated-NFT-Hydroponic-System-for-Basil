# Safety rules

All rules in this document run on the ESP32-S3. The Raspberry Pi can ask for a dose. It cannot force a pump to run, and it cannot turn a safety check off.

If the USB cable is disconnected, these rules keep running. No new dose from the Pi is applied. A pump that is already on still stops at its deadline.

## Rule summary

| ID | Rule | What the ESP32-S3 does |
| --- | --- | --- |
| S1 | Low water level | Stop circulation and stop every dosing pump. Reject new dose requests with `level_low`. |
| S2 | Invalid required sensor | Reject dosing that depends on that sensor. See the sensor table. |
| S3 | Circulation must be moving before a dose | Reject nutrient and pH doses with `circulation_off` unless the circulation pump is on and flow is valid. |
| S4 | One dosing pump at a time | Reject a second dosing pump with `pump_conflict`. |
| S5 | Solution A and Solution B stay apart | They never run together. After one stops, wait at least 10 seconds before the other may start. |
| S6 | pH Up and pH Down stay apart | They never run together. After one stops, wait at least 10 seconds before the other may start. |
| S7 | Stop deadline on every pump start | Store the stop time when the pump starts. Turn the pump off at that time inside the ESP32-S3 loop. |
| S8 | Maximum dose length | Reject `duration_ms` above the actuator maximum with `duration_too_long`. |
| S9 | Lost serial link | Keep S1–S8. Do not start a new dose. Keep circulation on only while level and flow checks pass. |
| S10 | Optional valves | Leave backup retention valves in the normal NFT path. They are not part of the first control loop. |

## S1. Water level

The level sensor must show that the tank is at or above the minimum mark.

- If the level is low, circulation turns off. This avoids running the circulation pump dry.
- Every dosing pump turns off, including one that was in the middle of a pulse.
- New requests are rejected with reason `level_low`.
- Recovery is automatic only after the level is safe again and the readings are stable for at least 5 seconds. A single good sample is not enough.

The optional fresh-water pump has a second limit: if the tank is at the high mark, a `fresh_water` request is rejected with `tank_full` so the dose does not overflow the tank. A low level also rejects fresh water, because the pump inlet may be dry.

## S2. Sensor validity

A required reading is invalid when the device does not respond, the value is outside the range in [sensors_table.md](sensors_table.md), or the sample is older than 5 seconds.

| Invalid reading | Dosing that stops |
| --- | --- |
| pH or ADS1115 | pH Up and pH Down |
| EC or ADS1115 | Solution A, Solution B, and fresh water |
| DS18B20 water temperature | All dosing pumps |
| Water level | All pumps, including circulation |
| Flow, while circulation is commanded on | Circulation and all dosing pumps |
| Air temperature and humidity | None. The fault is logged only. |
| BH1750 | None. The light field is left empty. |

The ESP32-S3 does not reuse an old pH or EC value to justify a new dose.

## S3. Mix the dose

Nutrient and pH pumps add liquid into the mixing tank. Circulation must already be running, and the flow sensor must show flow above the minimum, before those pumps start.

If circulation is off, or flow is missing, the request is rejected with `circulation_off`. If flow disappears during a dose, the dosing pump stops immediately.

## S4, S5, and S6. Conflicts

At most one of these pumps runs at a time:

- Solution A
- Solution B
- pH Up
- pH Down
- fresh water

Circulation may run at the same time as one dosing pump. That is how the tank mixes.

Concentrated Solution A and Solution B must not meet in the lines. pH Up and pH Down must not be added together. The ESP32-S3 enforces both the overlap ban and the 10 second gap. A request that breaks either rule is rejected with `pump_conflict`.

## S7 and S8. Time limits

Maximum run times are owned by the ESP32-S3:

| Pump | Maximum `duration_ms` |
| --- | --- |
| Solution A | 5000 |
| Solution B | 5000 |
| pH Up | 3000 |
| pH Down | 3000 |
| Fresh water | 15000 |
| Circulation | Controlled locally from level and flow. A Pi message cannot set an unlimited on-time. |

When a dose is accepted, the firmware computes `stop_at = now + duration_ms`, starts the pump, and turns it off when `now >= stop_at`. This check is in the main loop. It does not depend on a timer message from the Raspberry Pi.

A request with a missing duration, a duration below 1 ms, or a duration above the maximum is rejected with `duration_too_long` (or `bad_message` when the field is missing or not a number).

If a safety fault trips while a pump is on, the pump stops at once. The deadline is the latest allowed stop, not a promise to finish the pulse.

## S9. Serial disconnect

The ESP32-S3 treats the link as down when no complete JSON line has been received for 10 seconds. Telemetry may still be sent.

While the link is down:

- no queued dose request is started
- dosing pumps stay off unless a pulse was already accepted, in which case S7 still stops it
- circulation follows S1 and the flow check only

When the link returns, the Pi must send a new request. The ESP32-S3 does not replay an old `id`.

## S10. Valves

Optional backup valves stay in the position that leaves the normal NFT path open until a later milestone defines them. A dose request cannot move a valve. There is no valve name in the dosing pump list.

## What the Raspberry Pi is allowed to do

The Pi may:

- read telemetry
- log it
- display it
- send a `dose_request` that names one pump and one duration

The Pi may not:

- set a GPIO on the ESP32-S3
- clear a fault
- extend a deadline
- ask for two pumps in one message
- mark a request as urgent or unsafe-override

There is no override field in the protocol. See [communication_protocol.md](communication_protocol.md).
