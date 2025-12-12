// =====================================================================================
//  SafeSenior – Arduino UNO WiFi Rev2
// =====================================================================================
//
//  Behaviour:
//    Notifies backend when device goes ONLINE
//    Notifies backend when device goes OFFLINE
//    Toggles SOS alarm (blink + buzzer) on button press
//
//  Notes:
//    device_id is stored in EEPROM so it survives power loss
//    Button uses INPUT_PULLUP → idle=HIGH, pressed=LOW
// =====================================================================================

#include <SPI.h>
#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>
#include <EEPROM.h>

// -------------------- WIFI --------------------
const char* WIFI_SSID     = "6G";
const char* WIFI_PASSWORD = "netdogabi";

// -------------------- API --------------------
const char* API_HOST = "10.159.248.4";
const int   API_PORT = 8080;

const char* ENDPOINT_ONLINE   = "/device/online";
const char* ENDPOINT_OFFLINE  = "/device/offline";
const char* ENDPOINT_SOS      = "/sos";
const char* ENDPOINT_HELP_STATE = "/help/state/";

// -------------------- PINS --------------------
#define BUTTON_PIN  2
#define RED_LED     8
#define BLUE_LED    9
#define BUZZER_PIN  7

// -------------------- STATES --------------------
String deviceId = "";
bool sosActive = false;
int lastButtonState = HIGH;

// -------- Help (on the way) state check --------
HttpClient* helpClient = nullptr;
bool waitingHelpResponse = false;
unsigned long helpRequestStart = 0;
const unsigned long HELP_TIMEOUT = 1500;     // 1.5 seconds
const unsigned long HELP_INTERVAL = 2000;    // check every 2s
unsigned long lastHelpCheck = 0;
bool helpActive = false; 

// Max EEPROM storage available for the Arduino device
const int MY_EEPROM_SIZE = 512;

WiFiClient wifiClient;

// =====================================================================================
//Saves device_id permanently so it survives power loss
// =====================================================================================
void saveStringToEEPROM(int startAddr, const String& str) {

  // Write characters one by one until null terminator
  int len = str.length();
  for (int i = 0; i < len && (startAddr + i) < MY_EEPROM_SIZE - 1; i++) {
    EEPROM.update(startAddr + i, str[i]);
  }

  // Null terminator to mark end
  EEPROM.update(startAddr + len, '\0');
}

// =====================================================================================
// Loads a string from EEPROM (device_id)
// =====================================================================================
String readStringFromEEPROM(int startAddr) {

  // Read sequential bytes until null terminator or empty cell
  String result = "";
  for (int i = startAddr; i < MY_EEPROM_SIZE; i++) {
    byte b = EEPROM.read(i);
    if (b == '\0' || b == 0xFF) break;
    result += char(b);
  }

  return result;
}

// =====================================================================================
// Attempts Wi-Fi connection until success.
// =====================================================================================
void connectWiFi() {

  Serial.print("Connecting");

  // Try until connected
  while (WiFi.status() != WL_CONNECTED) {
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    delay(1000);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

// =====================================================================================
// Sends a POST request with JSON body
// =====================================================================================
bool httpPostJson(const char* path, const String& body, int& status, String& response) {

  // Prepare HTTP connection to the API
  HttpClient client(wifiClient, API_HOST, API_PORT);

  // Start POST request
  client.beginRequest();
  client.post(path);

  // Send headers
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Length", body.length());

  // Send payload
  client.beginBody();
  client.print(body);
  client.endRequest();

  // Read HTTP status and response
  status = client.responseStatusCode();
  response = client.responseBody();
  client.stop();
  return (status > 0);
}

// =====================================================================================
// Gets help-state (blue LED state) from API
// =====================================================================================
bool httpGetHelpState(bool& helpValue) {

  HttpClient client(wifiClient, API_HOST, API_PORT);

  // Build URL: /help/state/<device_id>
  String path = String(ENDPOINT_HELP_STATE) + deviceId;

  client.get(path);

  int status = client.responseStatusCode();
  String resp = client.responseBody();

  client.stop();

  if (status != 200) {
    return false;
  }

  // Detect if help (on the way) is true OR false
  helpValue = resp.indexOf("\"help\":true") != -1;
  return true;
}

// =====================================================================================
// Checks the help-on-the-way status from the backend at regular intervals
// =====================================================================================
void checkHelpOnTheWayStatus() {
  unsigned long now = millis();

  // Start a new request if enough time has passed
  if (!waitingHelpResponse && (now - lastHelpCheck >= HELP_INTERVAL)) {
    lastHelpCheck = now;

    helpClient = new HttpClient(wifiClient, API_HOST, API_PORT);
    String path = String(ENDPOINT_HELP_STATE) + deviceId;

    helpClient->get(path);
    waitingHelpResponse = true;
    helpRequestStart = now;
    return;
  }

  // Handle an ongoing request
  if (waitingHelpResponse) {
    // Response available
    if (helpClient->available()) {
      String resp = helpClient->responseBody();
      bool newHelp = resp.indexOf("\"help\":true") != -1 || resp.indexOf("\"help\": true") != -1;

    if (newHelp != helpActive) {
        helpActive = newHelp;

        if (newHelp) {
            digitalWrite(BLUE_LED, HIGH);
            Serial.println("Help on the way!");
        } else {
            digitalWrite(BLUE_LED, LOW);
            Serial.println("Help cancelled!");
        }
    }


      helpClient->stop();
      delete helpClient;
      helpClient = nullptr;
      waitingHelpResponse = false;
      return;
    }

    // Request timeout
    if (now - helpRequestStart > HELP_TIMEOUT) {
      Serial.println("[HELP] Request TIMEOUT — no response");
      
      helpClient->stop();
      delete helpClient;
      helpClient = nullptr;
      waitingHelpResponse = false;
      return;
    }
  }
}

// =====================================================================================
// Notifies API that device is online
// =====================================================================================
void sendDeviceOnline() {

  // Do nothing if no device_id is stored (device cannot identify itself yet)
  if (deviceId == "") return;

  // Prepare JSON payload
  String body = "{\"device_id\":\"" + deviceId + "\"}";

  int status;
  String resp;

  // Send POST
  Serial.println("Sending ONLINE");
  httpPostJson(ENDPOINT_ONLINE, body, status, resp);

  Serial.print("Status: ");
  if (status == 200)
    Serial.println("Ready!");
  else if (status == -3)
    Serial.println("Check IP addresses");
  else
    Serial.println(status);
}

// =====================================================================================
// Notifies API that device is offline
// =====================================================================================
void sendDeviceOffline() {

  if (deviceId == "") return;

  // Prepare JSON payload
  String body = "{\"device_id\":\"" + deviceId + "\"}";

  int status;
  String resp;

  // Send POST
  Serial.println("Sending OFFLINE");
  httpPostJson(ENDPOINT_OFFLINE, body, status, resp);

  Serial.print("Status: ");
  Serial.println(status);
}

// =====================================================================================
// Sends an SOS request to the backend and updates the device’s local alarm state.
// =====================================================================================
void toggleSOS() {

  // Build JSON payload
  String body = "{\"device_id\":\"" + deviceId + "\"}";

  int status;
  String resp;

  // Send SOS toggle request
  Serial.println("Sending SOS toggle...");
  httpPostJson(ENDPOINT_SOS, body, status, resp);

  Serial.print("SOS Status: ");
  Serial.println(status);
  Serial.println("Response: " + resp);

  // Flip local alarm state
  sosActive = !sosActive;
}

// =====================================================================================
//Prepare IO, load device_id, connect WiFi, notify online
// =====================================================================================
void setup() {

  // Initialize serial monitor
  Serial.begin(9600);
  // Waits until the USB connection is established
  while (!Serial);

  // Set pin modes for button, LEDs, and buzzer
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(RED_LED, OUTPUT);
  pinMode(BLUE_LED, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  helpActive = false;

  // Initialize LEDs on OFF state
  digitalWrite(RED_LED, LOW);
  digitalWrite(BLUE_LED, LOW);

  connectWiFi();

  deviceId = readStringFromEEPROM(0);

  // If no device_id exists, wait for user input
  if (deviceId.length() == 0) {

    Serial.println("Enter device ID:");
    while (deviceId.length() == 0) {
      if (Serial.available()) {
        deviceId = Serial.readStringUntil('\n');
        deviceId.trim();
      }
    }

    saveStringToEEPROM(0, deviceId);
  }

  Serial.print("Device ID: ");
  Serial.println(deviceId);

  // Start button state tracking
  lastButtonState = digitalRead(BUTTON_PIN);

  // Notify backend
  sendDeviceOnline();
}


// =====================================================================================
//  LOOP – Handle button presses, SOS blinking, and Wi-Fi reconnect
// =====================================================================================
void loop() {
  int btn = digitalRead(BUTTON_PIN);

  // Detect the moment the button is pressed (not held)
  // Avoids multiple triggers while the button is held down
  if (btn == LOW && lastButtonState == HIGH) {
    toggleSOS();
    delay(250);   // debounce
  }

  lastButtonState = btn;

  static unsigned long lastBlink = 0;
  // Faster beep when SOS only, slower beep when help is on the way
  unsigned long blinkInterval = helpActive ? 1000 : 500;

  static unsigned long lastBeep = 0;
  static bool isBeeping = false;

  unsigned long pauseTime  = helpActive ? 850 : 450; // pause duration
  unsigned long beepTime   = 150;                    // short beep, always the same

  if (sosActive) {
      unsigned long now = millis();

      if (!isBeeping) {
          // Check if it's time to beep
          if (now - lastBeep >= pauseTime) {
              tone(BUZZER_PIN, 500);  // short beep
              isBeeping = true;
              lastBeep = now;
          }
      } else {
          // If currently beeping, turn off 
          if (now - lastBeep >= beepTime) {
              noTone(BUZZER_PIN);
              isBeeping = false;
              lastBeep = now;
          }
      }

      // LED blinking logic stays unchanged
      static unsigned long lastBlinkLED = 0;
      unsigned long ledInterval = 500;
      if (now - lastBlinkLED >= ledInterval) {
          lastBlinkLED = now;
          static bool ledState = false;
          ledState = !ledState;
          digitalWrite(RED_LED, ledState ? HIGH : LOW);
      }

      checkHelpOnTheWayStatus();
  }
  else {
      digitalWrite(RED_LED, LOW);
      noTone(BUZZER_PIN);
      helpActive = false;
      digitalWrite(BLUE_LED, LOW);
  }

  // WI-FI reconnection 
  if (WiFi.status() != WL_CONNECTED) {
    sendDeviceOffline();
    connectWiFi();
    sendDeviceOnline();
  }
}
