# ESP32-S3 firmware

The ESP32-S3 is the local controller. It is the only board that reads sensors and drives pumps and valves.

## USB serial test

`main.cpp`, `communication.h`, and `communication.cpp` send fake sensor readings as one JSON object per line, every 2 seconds. They also read an optional command line from the Pi. The USB-UART port carries JSON only: there are no debug prints on that channel. No sensor is read and no pump pin is driven yet.

The board on this PC appears as a CP210x port, `COM5`. Build and upload with PlatformIO from this folder (`platformio.ini` targets that port). In the Arduino IDE, choose an ESP32 Dev Module and the same COM port.

The files below include this test and the planned layout for later milestones.

## Role

- Read pH, EC/TDS, water temperature, flow, water level, air temperature, humidity, and the optional light sensor.
- Check every reading before a dose is allowed.
- Turn pumps and valves on and off.
- Start a stop deadline with every pump. When the deadline arrives, the pump turns off even if the Raspberry Pi has stopped sending data.
- Send telemetry to the Raspberry Pi and accept or reject dose requests.

The Raspberry Pi must not toggle pump pins. A message from the Pi is a request. The firmware applies it only when the safety checks pass.

## Planned files

| File | Purpose |
| --- | --- |
| `main.cpp` | USB test loop now: read an optional command, then send one fake JSON frame every 2 seconds. Later: read, check, act, and communicate |
| `sensors.h`, `sensors.cpp` | Planned later: sensor drivers and a validity flag for each reading |
| `actuators.h`, `actuators.cpp` | Planned later: pump and valve outputs, timed pulses, and stop deadlines |
| `safety.h`, `safety.cpp` | Planned later: interlocks from [../docs/safety_rules.md](../docs/safety_rules.md) |
| `communication.h`, `communication.cpp` | USB serial JSON for this test. One fake reading per line, plus an optional command |

## Loop order

Each pass of the main loop will follow this order:

1. Read sensors.
2. Update safety status from those readings.
3. Stop any pump whose deadline has passed.
4. Apply only the dose requests that safety allows.
5. Send one telemetry line to the Raspberry Pi.

Safety and deadlines run on the ESP32-S3. They do not wait for a reply from the Pi.

## Related documents

- [../docs/system_architecture.md](../docs/system_architecture.md)
- [../docs/sensors_table.md](../docs/sensors_table.md)
- [../docs/actuators_table.md](../docs/actuators_table.md)
- [../docs/safety_rules.md](../docs/safety_rules.md)
- [../docs/milestones.md](../docs/milestones.md)
