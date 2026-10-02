// OneShot Arm v5 — UNO R3 motion firmware (3 × SG90 + 28BYJ-48/ULN2003 yaw). No servo driver board needed.
// Commands arrive one per line on Serial (115200) — from the ESP32-CAM bridge (pins D0/D1) or the Mac over USB.
//   P              ping                         -> "OK P"
//   S              status                       -> "OK S yaw sh el grip estop door moving"
//   J y s e [ms]   move joints (deg) smoothly   -> "OK J" when started, "DONE J" when finished
//   G pct [ms]     gripper 0 (open) .. 100 (closed)
//   H              home (all joints to 0, gripper open)
//   Z              set the current yaw as 0 (no yaw switch on v5)
//   X              stop now (holds position, servos stay powered, yaw coils off)
// Joint angles are ARM angles. Shoulder/elbow have 2:1 printed gears (v5), so servo moves 2° per joint degree.
// Safety: E-stop cuts the servo/stepper 5 V rail in hardware; D2 senses that rail. D3 = door interlock (kit button).
#include <Servo.h>

const uint8_t PIN_SH = 9, PIN_EL = 10, PIN_GR = 11;          // servo signals
const uint8_t PIN_IN[4] = {4, 5, 6, 7};                       // ULN2003 IN1..IN4
const uint8_t PIN_RAIL_SENSE = 2;                             // HIGH = motor rail powered (E-stop released)
const uint8_t PIN_DOOR = 3;                                   // LOW = door closed (button to GND, pull-up)

// ---- calibration: edit after the first power-up (see oneshot_v5/WIRING.md "Calibrate") ----
const float GEAR_SH = 2.0, GEAR_EL = 2.0;                     // servo deg per joint deg
const int US_MIN = 500, US_MAX = 2500;                        // SG90 pulse range for 0..180°
float SERVO_ZERO_SH = 90, SERVO_ZERO_EL = 90;                 // servo angle when the joint is at 0°
float SIGN_SH = 1, SIGN_EL = -1;                              // flip if a joint moves the wrong way
const float GRIP_OPEN = 40, GRIP_CLOSED = 115;                // servo deg; v4 test: contact ~88°, stall past ~91° on a cube
const float LIM_YAW = 150, LIM_SH_LO = -40, LIM_SH_HI = 45, LIM_EL_LO = -45, LIM_EL_HI = 45;   // joint deg
const float YAW_STEPS_PER_DEG = 4096.0 * 2.0 / 360.0;         // half-step 4096/rev × 16:32 gear = 22.76 steps/°
const unsigned YAW_US_PER_STEP = 1400;                        // ~31 °/s at the turret (v5 design 35 °/s)

Servo sSh, sEl, sGr;
float cur[4] = {0, 0, 0, 0}, from[4], to[4];                  // yaw, shoulder, elbow, grip(%)
unsigned long t0 = 0, dur = 0;
bool moving = false, attached = false;
long yawSteps = 0;
uint8_t phase = 0;
unsigned long lastStep = 0;
String line;

const uint8_t HALF[8][4] = {{1,0,0,0},{1,1,0,0},{0,1,0,0},{0,1,1,0},{0,0,1,0},{0,0,1,1},{0,0,0,1},{1,0,0,1}};

bool railOn() { return digitalRead(PIN_RAIL_SENSE) == HIGH; }
bool doorClosed() { return digitalRead(PIN_DOOR) == LOW; }

void coils(bool on) { for (uint8_t i = 0; i < 4; i++) digitalWrite(PIN_IN[i], on ? HALF[phase][i] : 0); }

void stepYaw(int dir) {
  phase = (phase + (dir > 0 ? 1 : 7)) & 7;
  coils(true);
  yawSteps += dir;
}

int servoUs(float servoDeg) { return US_MIN + (int)((constrain(servoDeg, 0, 180) / 180.0) * (US_MAX - US_MIN)); }

void writeServos(const float j[4]) {
  if (!attached) return;
  sSh.writeMicroseconds(servoUs(SERVO_ZERO_SH + SIGN_SH * GEAR_SH * j[1]));   // 0.1°-class resolution
  sEl.writeMicroseconds(servoUs(SERVO_ZERO_EL + SIGN_EL * GEAR_EL * j[2]));
  sGr.writeMicroseconds(servoUs(GRIP_OPEN + (GRIP_CLOSED - GRIP_OPEN) * j[3] / 100.0));
}

void attachAll() {
  if (attached) return;
  sSh.attach(PIN_SH); sEl.attach(PIN_EL); sGr.attach(PIN_GR);
  attached = true;
  writeServos(cur);
}

void detachAll() { sSh.detach(); sEl.detach(); sGr.detach(); attached = false; coils(false); moving = false; }

float minJerk(float s) { return s * s * s * (10 - 15 * s + 6 * s * s); }   // smooth start and stop

bool startMove(float y, float s, float e, float g, unsigned long ms) {
  if (!railOn()) { Serial.println("ERR ESTOP"); return false; }
  if (!doorClosed()) { Serial.println("ERR DOOR"); return false; }
  if (fabs(y) > LIM_YAW || s < LIM_SH_LO || s > LIM_SH_HI || e < LIM_EL_LO || e > LIM_EL_HI || g < 0 || g > 100) {
    Serial.println("ERR RANGE"); return false;
  }
  attachAll();
  for (uint8_t i = 0; i < 4; i++) from[i] = cur[i];
  to[0] = y; to[1] = s; to[2] = e; to[3] = g;
  float yawMs = fabs(y - cur[0]) * YAW_STEPS_PER_DEG * YAW_US_PER_STEP / 1000.0;
  dur = max(ms, (unsigned long)(yawMs * 1.9));               // min-jerk peak speed is 1.875× average: keep the stepper able to follow
  t0 = millis();
  moving = true;
  return true;
}

void status() {
  Serial.print("OK S "); Serial.print(cur[0], 1); Serial.print(' '); Serial.print(cur[1], 1); Serial.print(' ');
  Serial.print(cur[2], 1); Serial.print(' '); Serial.print(cur[3], 0); Serial.print(' ');
  Serial.print(railOn() ? "rail" : "ESTOP"); Serial.print(' '); Serial.print(doorClosed() ? "door_closed" : "DOOR_OPEN");
  Serial.print(' '); Serial.println(moving ? "moving" : "idle");
}

void handle(String c) {
  c.trim();
  if (!c.length()) return;
  char k = toupper(c[0]);
  float a[5] = {0, 0, 0, 0, 0}; int n = 0;
  int p = 1;
  while (n < 5 && p < (int)c.length()) {
    while (p < (int)c.length() && c[p] == ' ') p++;
    if (p >= (int)c.length()) break;
    a[n++] = c.substring(p).toFloat();
    while (p < (int)c.length() && c[p] != ' ') p++;
  }
  if (k == 'P') Serial.println("OK P");
  else if (k == 'S') status();
  else if (k == 'X') { moving = false; coils(false); Serial.println("OK X"); }
  else if (k == 'Z') { cur[0] = 0; yawSteps = 0; Serial.println("OK Z"); }
  else if (k == 'H') { if (startMove(0, 0, 0, 0, 1500)) Serial.println("OK H"); }
  else if (k == 'J' && n >= 3) { if (startMove(a[0], a[1], a[2], cur[3], n >= 4 ? a[3] : 1000)) Serial.println("OK J"); }
  else if (k == 'G' && n >= 1) { if (startMove(cur[0], cur[1], cur[2], a[0], n >= 2 ? a[1] : 600)) Serial.println("OK G"); }
  else Serial.println("ERR CMD");
}

void setup() {
  Serial.begin(115200);
  for (uint8_t i = 0; i < 4; i++) pinMode(PIN_IN[i], OUTPUT);
  pinMode(PIN_RAIL_SENSE, INPUT);                            // external 10k series + 100k pull-down (WIRING.md)
  pinMode(PIN_DOOR, INPUT_PULLUP);
  coils(false);
  Serial.println("OneShot v5 UNO ready");                     // servos stay detached until the first move
}

void loop() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n') { handle(line); line = ""; }
    else if (ch != '\r' && line.length() < 60) line += ch;
  }
  if (attached && !railOn()) { detachAll(); Serial.println("EVT ESTOP"); }
  if (moving && !doorClosed()) { moving = false; coils(false); Serial.println("EVT DOOR"); }
  if (!moving) return;
  float s = dur ? constrain((millis() - t0) / (float)dur, 0, 1) : 1;
  float f = minJerk(s);
  for (uint8_t i = 1; i < 4; i++) cur[i] = from[i] + (to[i] - from[i]) * f;
  writeServos(cur);
  long target = lround((from[0] + (to[0] - from[0]) * f) * YAW_STEPS_PER_DEG);
  if (target != yawSteps && micros() - lastStep >= YAW_US_PER_STEP) { lastStep = micros(); stepYaw(target > yawSteps ? 1 : -1); }
  cur[0] = yawSteps / YAW_STEPS_PER_DEG;
  if (s >= 1 && target == yawSteps) { moving = false; coils(false); Serial.println("DONE"); }   // 28BYJ holds by friction
}
