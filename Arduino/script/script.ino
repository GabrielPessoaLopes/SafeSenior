// ----------------------------------------------------------------------------
//  SafeSenior Embedded Alarm System
//  Functionality:
//  - Monitors a physical SOS button
//  - Activates LED and buzzer when pressed
//  - Sends HTTP POST alert to backend API via Wi-Fi connection
//  Board: ESP32 / ESP8266 (must support Wi-Fi)
// -----------------------------------------------------------------------------

#include <WiFi.h>          // Wi-Fi library for ESP32 (use <ESP8266WiFi.h> for ESP8266)
#include <HTTPClient.h>    // HTTP client for sending POST requests

// ------------------------- WIFI CONFIGURATION -------------------------------
const char* ssid = "YOUR_WIFI_SSID";                   // Wi-Fi network name (SSID)
const char* password = "YOUR_WIFI_PASSWORD";           // Wi-Fi password
const char* apiURL = "https://your-flask-api.vercel.app/sos";  // API endpoint for SOS alerts
const char* token = "Bearer <USER_JWT_TOKEN>";   // Provided during setup

String deviceId = "";

// --------------------------- DEFINITIONS -------------------------------------
int buttonPin = 2;          // Pin for SOS button
int ledPin = 8;             // Pin for LED indicator
int buzzerPin = 7;          // Pin for Buzzer
int tonePitch = 500;        // Buzzer tone frequency (Hz)

// ------------------------- SYSTEM STATE VARIABLES ---------------------------
bool systemActive = false;  // Tracks whether SOS mode is active
int lastButtonState = LOW;  // Stores previous button state for edge detection

// ------------------------- TIMING VARIABLES ---------------------------------
unsigned long previousMillis = 0;       // Timestamp for previous beep cycle
unsigned long toneStartMillis = 0;      // Timestamp for current tone start
unsigned long interval = 600;           // Interval between beep cycles (ms)
unsigned long toneDuration = 300;       // Duration of each tone (ms)
bool tonePlaying = false;               // Tracks whether a tone is currently active

// -----------------------------------------------------------------------------
//  setup()
//  Initializes serial communication, pin modes, and Wi-Fi connection
// -----------------------------------------------------------------------------
void setup() {
  pinMode(buttonPin, INPUT);       // Set button pin as input
  pinMode(ledPin, OUTPUT);         // Set LED pin as output
  pinMode(buzzerPin, OUTPUT);      // Set buzzer pin as output
  Serial.begin(9600);              // Start serial monitor for debugging

  // Connect to Wi-Fi network
  Serial.print("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");             // Print dots while attempting connection
  }
  Serial.println("\nConnected to WiFi!");

   getDeviceId();
}

// -----------------------------------------------------------------------------
//  loop()
//  Continuously checks for button press, toggles alarm state, and manages
//  LED/buzzer signaling based on timing logic
// -----------------------------------------------------------------------------
void loop() {
  int currentButtonState = digitalRead(buttonPin);  // Read current button state

  // Detects button press and changes system state
  if (currentButtonState == HIGH && lastButtonState == LOW) {
    systemActive = !systemActive;   // Change alarm state
    delay(150);                     // Debounce delay

    // When system activates, send SOS alert to backend
    if (systemActive)
      sendSOSAlert();
  }
  // Store current state for next loop
  lastButtonState = currentButtonState;  

  // --- Alarm activated ---
  if (systemActive) {
    unsigned long currentMillis = millis();

    // New beep cycle at defined intervals
    if (currentMillis - previousMillis >= interval) {
      previousMillis = currentMillis;
      tonePlaying = true;
      toneStartMillis = currentMillis;

      // Turn LED ON
      digitalWrite(ledPin, HIGH);       
      // Start buzzer
      tone(buzzerPin, tonePitch);      
    }

    // Stop tone after the defined duration
    if (tonePlaying && (currentMillis - toneStartMillis >= toneDuration)) {
      noTone(buzzerPin);                // Stop buzzer
      tonePlaying = false;
      digitalWrite(ledPin, LOW);        // Turn LED OFF
    }

  // --- Alarm off ---
  } else {
    // LED and buzzer fully off
    noTone(buzzerPin);
    digitalWrite(ledPin, LOW);
  }
}

// -----------------------------------------------------------------------------
//  sendSOSAlert()
//  Sends a POST request to the API when the SOS button is activated.
// -----------------------------------------------------------------------------
void sendSOSAlert() {
  // Test wifi connection
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    // Initialize connection to endpoint
    http.begin(apiURL);       
    // Define request format                    
    http.addHeader("Content-Type", "application/json"); 
    // JSON body to send in POST request
    String requestBody = "{\"device_id\": \"<UUID_of_device>\", \"triggered_by\": \"<owner_id>\"}";
    // Perform POST request
    int httpResponseCode = http.POST(requestBody);

    // Debug output
    if (httpResponseCode > 0) {
      Serial.print("API Response Code: ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print("Error sending alert, code: ");
      Serial.println(httpResponseCode);
    }

    http.end();  // Close HTTP connection to free memory

  } else {
    // Handle Wi-Fi disconnection gracefully
    Serial.println("WiFi not connected, alert not sent.");
  }
}

// -----------------------------------------------------------------------------
//  getDeviceId()
//  Sends a get request to the API to get device ID
// -----------------------------------------------------------------------------
void getDeviceId() {
if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(apiURL);
    http.addHeader("Authorization", token);

    int code = http.GET();
    if (code == 200) {
      String response = http.getString();
      int idIndex = response.indexOf("\"device_id\":\"");
      if (idIndex > 0) {
        int start = idIndex + 13;
        int end = response.indexOf("\"", start);
        deviceId = response.substring(start, end);
        Serial.print("Device ID from API: ");
        Serial.println(deviceId);
      } else
        Serial.println("Device ID not found in response.");
    } else {
      Serial.print("Error fetching device ID: ");
      Serial.println(code);
    }
    http.end();
  } else
    Serial.println("WiFi not connected, cannot fetch device ID.");
}

