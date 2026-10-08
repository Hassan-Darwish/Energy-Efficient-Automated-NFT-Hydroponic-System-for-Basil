# Actuators

Every actuator is driven by a GPIO on the ESP32-S3, through a suitable driver (relay or MOSFET module rated for the pump). The Raspberry Pi has no actuator outputs.

Each pump start stores a stop deadline on the ESP32-S3. When that time is reached, the firmware turns the pump off. A lost USB connection does not extend a deadline.

The times below are project limits for short dosing pulses. They are small on purpose. A later milestone may lower them after measuring real pump flow. They must not be raised from a Pi message.

| Actuator | Required | Role | ESP32 maximum run time | Notes |
| --- | --- | --- | --- | --- |
| Solution A pump | Yes | Add concentrated nutrient stock A to the mixing tank | 5 seconds per dose | Never runs in the same window as Solution B. A gap of at least 10 seconds is required between A and B. |
| Solution B pump | Yes | Add concentrated nutrient stock B to the mixing tank | 5 seconds per dose | Never runs in the same window as Solution A. Same 10 second gap. |
| pH Up pump | Yes | Raise tank pH | 3 seconds per dose | Never runs while pH Down is on, or within 10 seconds after pH Down. |
| pH Down pump | Yes | Lower tank pH | 3 seconds per dose | Never runs while pH Up is on, or within 10 seconds after pH Up. |
| Fresh-water pump | Optional | Dilute the tank when EC is high | 15 seconds per dose | Used only if the pump is installed. Still blocked when level is high enough that the tank would overflow, and when level is too low to pump. |
| Circulation pump | Yes | Move solution from the mixing tank through the NFT channels and back | Runs only while level and flow checks pass. The ESP32-S3 re-checks this every loop. | Dosing is allowed only while this pump is running and flow is valid. If level is low or flow is lost, circulation stops. The Pi cannot start or extend this pump. |
| Backup retention valves | Optional | Isolate or hold water in a backup path | Commanded on or off; no dosing pulse | Not part of the first control loop. Default position is the normal NFT path. |

## Pump names on the serial link

Dose requests use these `pump` strings. Any other string is rejected with `unknown_pump`. `circulation` is rejected too, because the ESP32-S3 owns that pump.

| `pump` value | Actuator |
| --- | --- |
| `solution_a` | Solution A pump |
| `solution_b` | Solution B pump |
| `ph_up` | pH Up pump |
| `ph_down` | pH Down pump |
| `fresh_water` | Fresh-water pump |

Valves are not dosed through `dose_request`. Circulation is not dosed through `dose_request`. Both stay under local ESP32-S3 rules. See [communication_protocol.md](communication_protocol.md).

## Control rules that apply to every pump

- The ESP32-S3 is the only device that sets the output pin.
- A dose request asks for a duration. The firmware rejects a duration above the maximum in the table.
- The firmware also rejects a duration of zero or a missing duration.
- At most one dosing pump runs at a time. Circulation may run together with one dosing pump, because circulation is what mixes the dose into the tank.
- Solution A and Solution B are sequential, with a gap, so the concentrates do not mix in the lines.
- pH Up and pH Down are sequential, with a gap, so the two chemicals are not added together.
- If a safety fault appears while a dosing pump is on, that pump stops immediately. The deadline is the latest allowed stop, not a reason to keep running.

## Circulation

Circulation is the moving pump for NFT. The ESP32-S3 turns it on when the level is safe and flow can be checked, and it turns it off when the level is low or when flow is missing while the pump is on.

The Raspberry Pi does not send circulation commands. A `dose_request` that names `circulation` is rejected. Level and flow on the ESP32-S3 are the only control for this pump.

## Fresh water and valves

Build and test the system without the fresh-water pump and without the backup valves. Add them only after Solution A, Solution B, pH Up, pH Down, and circulation already obey the safety rules.

When the fresh-water pump is absent, the firmware rejects `fresh_water` with reason `pump_not_fitted`. The dashboard can hide that control.
