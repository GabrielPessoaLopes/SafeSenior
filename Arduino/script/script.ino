// =====================================================================================
//  SafeSenior IoT SOS Device (ESP32) - Auto Auth via Device ID
// =====================================================================================
#include <WiFi.h>
#include <HTTPClient.h>
#include <EEPROM.h>
#include <ArduinoJson.h>

// ---------------------------- CONFIGURATION ------------------------------------------
const char* WIFI_SSID     = "6G";
const char* WIFI_PASSWORD = "netdogabi";
const char* API_BASE_URL  = "https://your-flask-api.vercel.app";
const char* LOGIN_ENDPOINT = "/devices/login";
const char* SOS_ENDPOINT   = "/sos";
const char* NOTIF_ENDPOINT = "/notifications";

#define BUTTON_PIN  2
#define RED_LED     8
#define BLUE_LED    9
#define BUZZER_PIN  7

bool sosActive = false;
String deviceId = "";
String jwtToken = "";

unsigned long lastPoll = 0;
const unsigned long POLL_INTERVAL = 10000;
const int EEPROM_SIZE = 512;

// =====================================================================================
//  Wi-Fi connection
// =====================================================================================
void connectWiFi() {
  Serial.print("Connecting to Wi-Fi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected!");
}

// =====================================================================================
//  EEPROM helpers
// =====================================================================================
void saveStringToEEPROM(int startAddr, const String& str) {
  for (int i = 0; i < str.length(); ++i) EEPROM.write(startAddr + i, str[i]);
  EEPROM.write(startAddr + str.length(), '\0');
  EEPROM.commit();
}

String readStringFromEEPROM(int startAddr) {
  String str = "";
  for (int i = startAddr; i < EEPROM_SIZE; ++i) {
    char c = EEPROM.read(i);
    if (c == '\0') break;
    str += c;
  }
  return str;
}

// =====================================================================================
//  Device login (get JWT)
// =====================================================================================
bool getDeviceToken() {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  String url = String(API_BASE_URL) + LOGIN_ENDPOINT;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  String body = "{\"device_id\":\"" + deviceId + "\"}";
  int code = http.POST(body);

  if (code == 200) {
    String response = http.getString();
    Serial.println("Login response: " + response);

    DynamicJsonDocument doc(512);
    deserializeJson(doc, response);
    jwtToken = doc["token"].as<String>();
    saveStringToEEPROM(100, jwtToken);
    http.end();
    return true;
  } else {
    Serial.print("Login failed. Code: ");
    Serial.println(code);
  }
  http.end();
  return false;
}

// =====================================================================================
//  Toggle SOS event
// =====================================================================================
void toggleSOS() {
  if (WiFi.status() != WL_CONNECTED || jwtToken == "") return;

  HTTPClient http;
  String url = String(API_BASE_URL) + SOS_ENDPOINT;
  http.begin(url);
  http.addHeader("Authorization", "Bearer " + jwtToken);
  http.addHeader("Content-Type", "application/json");

  int code = http.POST("{}");
  if (code > 0) {
    String response = http.getString();
    Serial.println("SOS response: " + response);
    sosActive = response.indexOf("\"active\":true") > 0;
    digitalWrite(RED_LED, sosActive);
    if (sosActive) tone(BUZZER_PIN, 500, 250);
  }
  http.end();
}

// =====================================================================================
//  Check notifications (polling)
// =====================================================================================
void checkNotifications() {
  if (WiFi.status() != WL_CONNECTED || jwtToken == "") return;

  HTTPClient http;
  String url = String(API_BASE_URL) + NOTIF_ENDPOINT;
  http.begin(url);
  http.addHeader("Authorization", "Bearer " + jwtToken);

  int code = http.GET();
  if (code == 200) {
    String payload = http.getString();
    Serial.println("Notifications: " + payload);
    digitalWrite(BLUE_LED, payload.indexOf("help_on_the_way") > 0 ? HIGH : LOW);
  }
  http.end();
}

// =====================================================================================
//  setup()
// =====================================================================================
void setup() {
  Serial.begin(9600);
  EEPROM.begin(EEPROM_SIZE);

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(RED_LED, OUTPUT);
  pinMode(BLUE_LED, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  connectWiFi();

  // Read stored IDs
  deviceId = readStringFromEEPROM(0);
  jwtToken = readStringFromEEPROM(100);

  if (deviceId == "") {
    Serial.println("Enter device ID (from backend): ");
    while (deviceId == "") {
      if (Serial.available()) {
        deviceId = Serial.readStringUntil('\n');
        deviceId.trim();
        saveStringToEEPROM(0, deviceId);
      }
    }
  }

  Serial.println("Device ID: " + deviceId);

  if (jwtToken == "" || jwtToken.length() < 20) {
    Serial.println("Fetching new token...");
    getDeviceToken();
  } else {
    Serial.println("Using stored token.");
  }
}

// =====================================================================================
//  loop()
// =====================================================================================
void loop() {
  static int lastButton = HIGH;
  int current = digitalRead(BUTTON_PIN);

  if (current == LOW && lastButton == HIGH) {
    toggleSOS();
    delay(300);
  }
  lastButton = current;

  unsigned long now = millis();
  if (now - lastPoll >= POLL_INTERVAL) {
    checkNotifications();
    lastPoll = now;
  }
}
