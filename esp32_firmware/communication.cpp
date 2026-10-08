#include "communication.h"

#include <esp_system.h>

// One JSON object per line. Nothing else may be written to Serial.
// A missing or invalid command is ignored so the loop keeps running.

static const unsigned long SEND_PERIOD_MS = 2000;
static const char* DEVICE_ID = "esp32_hydro_001";

static const int LEVEL_MIN = 40;
static const float PH_LOW = 5.5f;
static const float PH_HIGH = 6.5f;
static const int EC_LOW = 700;
static const int EC_HIGH = 1200;

static uint32_t lastSendMs = 0;
static unsigned long sequence = 1;

static float ph = 6.2f;
static int ecTds = 850;
static int waterLevel = 75;
static float waterTemperature = 24.5f;
static float flowRate = 1.2f;
static float airTemperature = 27.0f;
static int humidity = 60;
static int lightIntensity = 500;

// Last command from the Pi. Stored only. GPIO stays untouched in this test.
static String lastAction = "no_action";
static int lastDurationSeconds = 0;
static String lastReason = "monitoring_only";

static const char* KNOWN_ACTIONS[] = {
    "no_action",
    "ph_up",
    "ph_down",
    "nutrient_a",
    "nutrient_b",
    "fresh_water",
    "circulation_on",
    "circulation_off",
    "valve_open",
    "valve_close",
    "fan_on",
    "fan_off",
    "led_on",
    "led_off",
};

static void formatDecimal(char* out, size_t size, float value, int decimals) {
  // Build the number from integers so the frame does not depend on %f support.
  bool negative = value < 0.0f;
  float magnitude = negative ? -value : value;
  int scale = 1;
  for (int i = 0; i < decimals; i++) {
    scale *= 10;
  }
  int scaled = (int)(magnitude * (float)scale + 0.5f);
  int whole = scaled / scale;
  int fraction = scaled % scale;
  if (decimals <= 0) {
    snprintf(out, size, "%s%d", negative ? "-" : "", whole);
    return;
  }
  snprintf(out, size, "%s%d.%0*d", negative ? "-" : "", whole, decimals, fraction);
}

static float walkFloat(float value, float step, float low, float high) {
  int delta = random(-1000, 1001);
  value += (delta / 1000.0f) * step;
  if (value < low) {
    value = low;
  }
  if (value > high) {
    value = high;
  }
  return value;
}

static int walkInt(int value, int step, int low, int high) {
  value += random(-step, step + 1);
  if (value < low) {
    value = low;
  }
  if (value > high) {
    value = high;
  }
  return value;
}

static void pushOneFault() {
  int choice = random(0, 5);
  if (choice == 0) {
    waterLevel = random(20, LEVEL_MIN);
  } else if (choice == 1) {
    ph = 6.7f + (random(0, 6) / 10.0f);
  } else if (choice == 2) {
    ph = 5.0f + (random(0, 4) / 10.0f);
  } else if (choice == 3) {
    ecTds = random(EC_HIGH + 50, 1401);
  } else {
    ecTds = random(500, EC_LOW - 49);
  }
}

static void stepFakeSensors() {
  ph = walkFloat(ph, 0.05f, 5.0f, 7.2f);
  ecTds = walkInt(ecTds, 15, 500, 1400);
  waterLevel = walkInt(waterLevel, 1, 20, 100);
  waterTemperature = walkFloat(waterTemperature, 0.2f, 18.0f, 30.0f);
  flowRate = walkFloat(flowRate, 0.05f, 0.6f, 2.2f);
  airTemperature = walkFloat(airTemperature, 0.3f, 20.0f, 34.0f);
  humidity = walkInt(humidity, 1, 35, 85);
  lightIntensity = walkInt(lightIntensity, 20, 150, 900);
  // A rare out-of-range sample lets the Pi show a non-NORMAL status.
  if (sequence > 1 && random(0, 100) < 12) {
    pushOneFault();
  }
}

static const char* statusForReadings() {
  if (waterLevel < LEVEL_MIN) {
    return "ALARM";
  }
  if (ph < PH_LOW || ph > PH_HIGH || ecTds < EC_LOW || ecTds > EC_HIGH) {
    return "WARNING";
  }
  return "NORMAL";
}

static bool knownAction(const String& action) {
  size_t count = sizeof(KNOWN_ACTIONS) / sizeof(KNOWN_ACTIONS[0]);
  for (size_t i = 0; i < count; i++) {
    if (action == KNOWN_ACTIONS[i]) {
      return true;
    }
  }
  return false;
}

static bool readQuoted(const String& line, const char* key, String& value) {
  String pattern = String("\"") + key + "\"";
  int keyAt = line.indexOf(pattern);
  if (keyAt < 0) {
    return false;
  }
  int colon = line.indexOf(':', keyAt + pattern.length());
  if (colon < 0) {
    return false;
  }
  int openQuote = line.indexOf('"', colon + 1);
  if (openQuote < 0) {
    return false;
  }
  int closeQuote = line.indexOf('"', openQuote + 1);
  if (closeQuote < 0) {
    return false;
  }
  value = line.substring(openQuote + 1, closeQuote);
  return true;
}

static bool readInteger(const String& line, const char* key, int& value) {
  String pattern = String("\"") + key + "\"";
  int keyAt = line.indexOf(pattern);
  if (keyAt < 0) {
    return false;
  }
  int colon = line.indexOf(':', keyAt + pattern.length());
  if (colon < 0) {
    return false;
  }
  int start = colon + 1;
  while (start < (int)line.length() && line.charAt(start) == ' ') {
    start++;
  }
  int end = start;
  if (end < (int)line.length() && line.charAt(end) == '-') {
    end++;
  }
  while (end < (int)line.length() && isDigit(line.charAt(end))) {
    end++;
  }
  if (end == start) {
    return false;
  }
  value = line.substring(start, end).toInt();
  return true;
}

static void rememberCommand(const String& line) {
  if (line.length() == 0 || line.charAt(0) != '{') {
    return;
  }
  String action;
  if (!readQuoted(line, "action", action) || !knownAction(action)) {
    return;
  }
  int duration = 0;
  readInteger(line, "duration_seconds", duration);
  String reason;
  if (!readQuoted(line, "reason", reason)) {
    reason = "";
  }
  lastAction = action;
  lastDurationSeconds = duration;
  lastReason = reason;
  // Kept for a later milestone. This read makes the stored command count
  // without writing anything on the JSON channel.
  if (lastAction.length() == 0 && lastDurationSeconds < 0 && lastReason.length() == 0) {
    lastAction = "no_action";
  }
}

void communicationBegin() {
  // UART0 on the USB-UART chip (CP210x). Do not wait for the port to open:
  // the loop must keep running when the Pi is absent.
  Serial.begin(115200);
  randomSeed((uint32_t)esp_random());
  lastSendMs = millis() - SEND_PERIOD_MS;
}

void communicationReadCommand() {
  // Non-blocking: return at once when the Pi has not sent a line.
  static String line;
  while (Serial.available() > 0) {
    char letter = (char)Serial.read();
    if (letter == '\n') {
      rememberCommand(line);
      line = "";
    } else if (letter != '\r' && line.length() < 200) {
      line += letter;
    }
  }
}

void communicationSendIfDue() {
  uint32_t now = millis();
  if (now - lastSendMs < SEND_PERIOD_MS) {
    return;
  }
  lastSendMs = now;

  char phText[16];
  char waterTempText[16];
  char flowText[16];
  char airTempText[16];
  formatDecimal(phText, sizeof(phText), ph, 1);
  formatDecimal(waterTempText, sizeof(waterTempText), waterTemperature, 1);
  formatDecimal(flowText, sizeof(flowText), flowRate, 1);
  formatDecimal(airTempText, sizeof(airTempText), airTemperature, 1);

  char frame[384];
  snprintf(
      frame,
      sizeof(frame),
      "{\"protocol_version\":\"1.0\",\"device_id\":\"%s\",\"sequence\":%lu,"
      "\"ph\":%s,\"ec_tds\":%d,\"water_level\":%d,\"water_temperature\":%s,"
      "\"flow_rate\":%s,\"air_temperature\":%s,\"humidity\":%d,"
      "\"light_intensity\":%d,\"system_status\":\"%s\"}",
      DEVICE_ID,
      sequence,
      phText,
      ecTds,
      waterLevel,
      waterTempText,
      flowText,
      airTempText,
      humidity,
      lightIntensity,
      statusForReadings());

  Serial.println(frame);
  sequence++;
  stepFakeSensors();
}
