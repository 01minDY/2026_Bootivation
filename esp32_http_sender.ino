#include <HTTPClient.h>
#include <WiFi.h>

const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* CONTROL_URL = "http://192.168.0.10:8000/api/distance";

enum class DistanceLevel {
  SAFE,
  CAUTION,
  DANGER
};

DistanceLevel distanceLevelFor(float distanceM) {
  if (distanceM <= 1.0f) {
    return DistanceLevel::DANGER;
  }
  if (distanceM <= 3.0f) {
    return DistanceLevel::CAUTION;
  }
  return DistanceLevel::SAFE;
}

const char* distanceLevelText(DistanceLevel level) {
  switch (level) {
    case DistanceLevel::DANGER:
      return "DANGER";
    case DistanceLevel::CAUTION:
      return "CAUTION";
    default:
      return "SAFE";
  }
}

bool sendDistance(float distanceM, DistanceLevel distanceLevel) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  String body = "{\"distance_m\":";
  body += String(distanceM, 2);
  body += ",\"distance_level\":\"";
  body += distanceLevelText(distanceLevel);
  body += "\"}";

  HTTPClient http;
  http.begin(CONTROL_URL);
  http.addHeader("Content-Type", "application/json");
  const int statusCode = http.POST(body);
  http.end();

  return statusCode == 200;
}

bool sendMeasuredDistance(float distanceM) {
  return sendDistance(distanceM, distanceLevelFor(distanceM));
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
  }
}

void loop() {
  const float distanceFromWebcamM = 2.40f;
  sendMeasuredDistance(distanceFromWebcamM);
  delay(500);
}
