#include <Arduino.h>

#include "communication.h"

// USB serial test. Fake readings go out as JSON. Commands are optional.
// No sensor drivers and no pump pins in this milestone.

void setup() {
  communicationBegin();
}

void loop() {
  communicationReadCommand();
  communicationSendIfDue();
}
