/*
 * Optional ESP32 sender.
 *
 * The primary/easiest path is distance_sender.py on the measuring laptop.
 * If the ESP32 must transmit, call sendDistance() with the distance and stage
 * calculated by the laptop-side webcam program.
 */

#include <HTTPClient.h>
#include <WiFi.h>

const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* CONTROL_URL = "http://192.168.0.10:8000/api/distance";

bool sendDistance(float distanceM, const char* distanceLevel) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;
  http.begin(CONTROL_URL);
  http.addHeader("Content-Type", "application/json");

  String body = "{\"distance_m\":";
  body += String(distanceM, 2);
  body += ",\"distance_level\":\"";
  body += distanceLevel;
  body += "\"}";

  int status = http.POST(body);
  http.end();
  return status >= 200 && status < 300;
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
  }
}

void loop() {
  // Example only. Replace these with the latest values received/calculated
  // by your webcam-distance program.
  sendDistance(2.40, "CAUTION");
  delay(500);
}
