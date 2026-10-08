# Sensors

The ESP32-S3 reads every sensor in this table. A reading is valid only when the sensor responds and the value sits inside the physical range below. An invalid required reading blocks dosing. Circulation may also stop when level or flow is invalid. Details are in [safety_rules.md](safety_rules.md).

pH and EC/TDS are analog probes. They connect to an ADS1115 so the ESP32-S3 reads a stable digital value instead of using its own ADC.

| Sensor | Interface | Required | Purpose | Valid range | If the reading is missing or invalid |
| --- | --- | --- | --- | --- | --- |
| pH probe | ADS1115 analog input | Yes | Measure tank acidity for basil | 0.0 to 14.0 pH | Block pH dosing. Keep the last good value out of control decisions. |
| EC/TDS probe | ADS1115 analog input | Yes | Measure nutrient strength | 0.0 to 5.0 mS/cm EC | Block Solution A, Solution B, and fresh-water dosing. |
| ADS1115 | I2C | Yes | Convert pH and EC probe voltages | Device responds on I2C | Treat pH and EC as invalid. Block nutrient and pH dosing. |
| DS18B20 | 1-Wire | Yes | Water temperature in the tank | 5 °C to 45 °C | Block dosing. Temperature changes the meaning of EC and is required before a dose. |
| Flow sensor | Digital pulse | Yes | Confirm circulation through the NFT channels | Pulses match a flow above the minimum while the circulation pump is on | Stop circulation and block dosing until flow is credible again. |
| Water level sensor | Digital or analog level switch | Yes | Confirm the tank has enough water to pump | Level at or above the minimum mark | Stop circulation and block every dosing pump. |
| BME280 or AHT20 | I2C | Yes, one of the two | Air temperature and relative humidity around the crop | Air 5 °C to 50 °C, humidity 0% to 100% | Log the fault. Dosing may continue because these readings do not command pumps. Pick one sensor and wire only that one. |
| BH1750 | I2C | Optional | Light level at the canopy | 0 lx to 65535 lx | Leave the field empty in telemetry. No effect on pumps. |

## How each sensor is used

- **pH** decides whether a later dosing method asks for pH Up or pH Down.
- **EC/TDS** decides whether a later dosing method asks for Solution A and Solution B, or for fresh water when the optional dilution pump exists.
- **DS18B20** records water temperature with every sample. EC is interpreted together with temperature. A missing temperature reading blocks dosing.
- **Flow** confirms that the circulation pump is actually moving water, not only that its output pin is on.
- **Water level** is the main dry-run protection for every pump.
- **Air temperature and humidity** are logged for the grow environment. They are not pump commands.
- **BH1750** is logged when it is fitted, so light can be compared with growth notes later.

## Calibration

Calibration is part of the sensor milestone, before any automatic dose:

- pH: two-point calibration with standard buffers (typically pH 4 and pH 7).
- EC: calibration with a known conductivity standard, with the probe at a known water temperature.
- DS18B20: compare against a reference thermometer in the same water.
- Flow: confirm pulses while a measured volume passes, or confirm that flow is above the minimum during circulation.
- Level: confirm the switch changes at the chosen minimum mark in the tank.
- Air sensor: confirm the I2C device responds and the values are plausible for the room.
- BH1750, if fitted: confirm lux changes when the sensor is covered and uncovered.

Store calibration offsets in the ESP32-S3 firmware configuration when that milestone is implemented. The Raspberry Pi displays the calibrated values from telemetry. It does not apply a second calibration.

## Telemetry names

These names match [communication_protocol.md](communication_protocol.md):

| Sensor | JSON field |
| --- | --- |
| pH | `ph` |
| EC | `ec` |
| Water temperature | `water_temp_c` |
| Air temperature | `air_temp_c` |
| Air humidity | `air_humidity` |
| Light | `light_lux` (null if the BH1750 is absent) |
| Level | `level_ok` |
| Flow | `flow_lpm` |
