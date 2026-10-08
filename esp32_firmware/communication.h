#pragma once

#include <Arduino.h>

// USB serial JSON only. This milestone sends fake readings and remembers
// one optional command. It does not drive pumps, valves, or sensors.

void communicationBegin();
void communicationReadCommand();
void communicationSendIfDue();
