// OneShot Arm v5 — ESP32-CAM (AI-Thinker) camera + Wi-Fi bridge to the UNO.
// Board: "AI Thinker ESP32-CAM" in Arduino IDE (esp32 core 2.x/3.x). Flash it on the MB board once; after that use OTA.
// HTTP (port 80, every call needs ?k=API_KEY):
//   /capture[?flash=1]      one JPEG (what Claude looks at)
//   /cmd?c=J%2030%2010%200  send one line to the UNO, returns its reply lines (waits up to ?t= ms, default 3000)
//   /status                 bridge + UNO status
// Port 81: /stream          MJPEG for a browser.
// Safety: if a motion command was sent and no request arrives for 3 s, the bridge sends X (stop) to the UNO.
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>
#include "esp_camera.h"
#include "secrets.h"

// AI-Thinker camera pins
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22
#define FLASH_LED 4

// UART to the UNO: GPIO14 = TX -> UNO D0 (RX);  UNO D1 (TX) -> 1k/2k divider -> GPIO15 = RX
#define UNO_TX 14
#define UNO_RX 15
HardwareSerial Uno(1);

WebServer http(80), streamSrv(81);
unsigned long lastReq = 0;
bool motionPending = false;

bool authed(WebServer& s) {
  if (s.arg("k") != API_KEY) { s.send(401, "text/plain", "bad key"); return false; }
  lastReq = millis();
  return true;
}

String unoTalk(const String& cmd, unsigned long waitMs) {
  while (Uno.available()) Uno.read();                     // drop stale lines
  Uno.print(cmd); Uno.print('\n');
  String out, line;
  unsigned long t = millis();
  while (millis() - t < waitMs) {
    while (Uno.available()) {
      char c = Uno.read();
      if (c == '\n') {
        out += line + "\n";
        if (line.startsWith("ERR") || line.startsWith("DONE") || line.startsWith("OK S") || line == "OK P" ||
            line == "OK X" || line == "OK Z") return out;
        line = "";
      } else if (c != '\r') line += c;
    }
    delay(2);
  }
  return out + (line.length() ? line + "\n" : "") + "TIMEOUT\n";
}

void handleCapture() {
  if (!authed(http)) return;
  bool flash = http.arg("flash") == "1";
  if (flash) { digitalWrite(FLASH_LED, HIGH); delay(120); }
  camera_fb_t* fb = esp_camera_fb_get();                   // throw away one stale frame
  if (fb) esp_camera_fb_return(fb);
  fb = esp_camera_fb_get();
  if (flash) digitalWrite(FLASH_LED, LOW);
  if (!fb) { http.send(503, "text/plain", "camera failed"); return; }
  http.sendHeader("Cache-Control", "no-store");
  http.send_P(200, "image/jpeg", (const char*)fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

void handleCmd() {
  if (!authed(http)) return;
  String c = http.arg("c");
  unsigned long t = http.hasArg("t") ? http.arg("t").toInt() : 3000;
  char k = c.length() ? toupper(c[0]) : ' ';
  motionPending = (k == 'J' || k == 'G' || k == 'H');
  String r = unoTalk(c, constrain(t, 50UL, 20000UL));
  if (r.indexOf("DONE") >= 0 || r.startsWith("ERR")) motionPending = false;
  http.send(200, "text/plain", r);
}

void handleStatus() {
  if (!authed(http)) return;
  String r = "bridge ip=" + WiFi.localIP().toString() + " rssi=" + String(WiFi.RSSI()) + "\n" + unoTalk("S", 500);
  http.send(200, "text/plain", r);
}

void handleStream() {
  if (streamSrv.arg("k") != API_KEY) { streamSrv.send(401, "text/plain", "bad key"); return; }
  WiFiClient client = streamSrv.client();
  client.print("HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=f\r\n\r\n");
  while (client.connected()) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) break;
    client.printf("--f\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", fb->len);
    client.write(fb->buf, fb->len);
    client.print("\r\n");
    esp_camera_fb_return(fb);
    http.handleClient();                                   // keep commands responsive while streaming
    ArduinoOTA.handle();
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(FLASH_LED, OUTPUT); digitalWrite(FLASH_LED, LOW);
  Uno.begin(115200, SERIAL_8N1, UNO_RX, UNO_TX);
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0; c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM; c.pin_d1 = Y3_GPIO_NUM; c.pin_d2 = Y4_GPIO_NUM; c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM; c.pin_d5 = Y7_GPIO_NUM; c.pin_d6 = Y8_GPIO_NUM; c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM; c.pin_pclk = PCLK_GPIO_NUM; c.pin_vsync = VSYNC_GPIO_NUM; c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM; c.pin_pwdn = PWDN_GPIO_NUM; c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000; c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_SVGA; c.jpeg_quality = 12; c.fb_count = 2; c.grab_mode = CAMERA_GRAB_LATEST;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  if (esp_camera_init(&c) != ESP_OK) Serial.println("camera init FAILED (check ribbon + 5 V supply)");
  WiFi.mode(WIFI_STA); WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print('.'); }
  Serial.printf("\nIP %s  -> http://oneshot.local/capture?k=...\n", WiFi.localIP().toString().c_str());
  MDNS.begin("oneshot");
  ArduinoOTA.setHostname("oneshot"); ArduinoOTA.setPassword(API_KEY); ArduinoOTA.begin();
  http.on("/capture", handleCapture); http.on("/cmd", handleCmd); http.on("/status", handleStatus);
  http.begin();
  streamSrv.on("/stream", handleStream); streamSrv.begin();
}

void loop() {
  http.handleClient(); streamSrv.handleClient(); ArduinoOTA.handle();
  if (motionPending && millis() - lastReq > 3000) {        // the Mac went quiet mid-move: stop the arm
    Uno.print("X\n"); motionPending = false;
  }
}
