// FarmHand rail-SCARA motion controller (ESP32-S3).
// PC plans, this board executes and guards: watchdog, E-stop, permit lease, limits, following error.
// Protocol: include/protocol.h (JSON lines + CRC-16), contract docs/ARCHITECTURE.md D7.
#include <Arduino.h>
#include <ArduinoJson.h>
#include <FastAccelStepper.h>
#include <Wire.h>
#include <Adafruit_MCP23X17.h>
#include <Adafruit_ADS1X15.h>
#include <TMCStepper.h>
#include "config.h"
#include "protocol.h"
#include "supervisor.h"

using namespace fh;

static FastAccelStepperEngine engine;
static FastAccelStepper* ax[kAxes];
static Adafruit_MCP23X17 io;
static Adafruit_ADS1115 adc;
static HardwareSerial& TMC = Serial1;
static HardwareSerial& SERVO = Serial2;
static TMC2209Stepper* drv[4];
static Supervisor sup;

static float enc_unit[kAxes];          // encoder position in axis units
static float enc_zero[kAxes] = {0};
static float last_raw[kAxes] = {0};
static int32_t turns[kAxes] = {0};
static uint32_t seq_out = 0, last_status = 0;
static String rx;

// ---------- encoders: MT6701 SSI, 24-bit frame = 14-bit angle + 4 status + 6 CRC ----------
static uint32_t ssi_read(uint8_t cs) {
  digitalWrite(cs, LOW);
  delayMicroseconds(1);
  uint32_t v = 0;
  for (int i = 0; i < 24; ++i) {
    digitalWrite(cfg::SSI_CLK, LOW); delayMicroseconds(1);
    digitalWrite(cfg::SSI_CLK, HIGH); delayMicroseconds(1);
    v = (v << 1) | digitalRead(cfg::SSI_DATA);
  }
  digitalWrite(cs, HIGH);
  return v;
}

static void read_encoders() {
  for (int i = 0; i < kAxes; ++i) {
    float frac = ((ssi_read(cfg::ENC_CS[i]) >> 10) & 0x3FFF) / 16384.0f;   // 0..1 rev
    if (cfg::ENC_MULTITURN[i]) {
      float d = frac - last_raw[i];
      if (d < -0.5f) turns[i]++;
      if (d > 0.5f) turns[i]--;
    }
    last_raw[i] = frac;
    float u = (turns[i] + frac) * cfg::ENC_UNITS_PER_REV[i];
    if (!cfg::ENC_MULTITURN[i] && u > 180.0f) u -= 360.0f;             // joints report -180..180
    enc_unit[i] = u - enc_zero[i];
  }
}

static float cmd_unit(int i) { return ax[i]->getCurrentPosition() / cfg::STEPS_PER_UNIT[i]; }

// ---------- outgoing ----------
static void send(JsonDocument& d) {
  d["seq"] = ++seq_out;
  String s;
  serializeJson(d, s);
  s.remove(s.length() - 1);                    // drop the closing brace, seal() re-adds it with crc
  Serial.println(seal(std::string(s.c_str())).c_str());
}
static void reply(uint32_t seq, bool ok, Err e = Err::NONE) {
  JsonDocument d;
  d["evt"] = ok ? "ack" : "nak";
  d["re"] = seq;
  if (!ok) d["err"] = err_name(e);
  send(d);
}
static void status() {
  JsonDocument d;
  d["evt"] = "status";
  d["state"] = state_name(sup.state());
  d["err"] = err_name(sup.error());
  d["inside"] = sup.inside_printer();
  JsonArray j = d["enc"].to<JsonArray>(), c = d["cmd"].to<JsonArray>();
  for (int i = 0; i < kAxes; ++i) { j.add(enc_unit[i]); c.add(cmd_unit(i)); }
  d["estop"] = digitalRead(cfg::ESTOP_SENSE) == HIGH;
  d["bus_v"] = adc.computeVolts(adc.readADC_SingleEnded(2)) * 11.0f;    // 100k/10k divider
  send(d);
}

// ---------- motion ----------
static void all_stop(bool hard) {
  for (int i = 0; i < kAxes; ++i) hard ? ax[i]->forceStop() : ax[i]->stopMove();
  io.digitalWrite(cfg::BEACON, LOW);
}

static bool home_axes() {   // blocking: switch for coarse zero, then absolute encoder offset (Dummy trick, D209)
  sup.start_homing();
  const int order[kAxes] = {1, 0, 2, 3, 4};   // Z first (lift clear), then X, then the arm
  for (int k = 0; k < kAxes; ++k) {
    int i = order[k];
    ax[i]->setSpeedInHz(cfg::HOME_SPEED[i] * cfg::STEPS_PER_UNIT[i]);
    ax[i]->runBackward();
    uint32_t t0 = millis();
    while (io.digitalRead(cfg::SW_HOME[i]) == HIGH) {          // switches are NC-to-GND, HIGH = not reached
      sup.heartbeat(millis());                                  // homing is supervised locally by the timeout
      if (sup.tick(millis(), digitalRead(cfg::ESTOP_SENSE) == HIGH, false) || millis() - t0 > 60000) {
        all_stop(true); sup.homing_done(false); return false;
      }
      delay(1);
    }
    ax[i]->forceStopAndNewPosition(0);
    read_encoders();
    enc_zero[i] += enc_unit[i];                                 // encoder reads 0 at the switch
    turns[i] = 0;
  }
  sup.homing_done(true);
  return true;
}

static void start_move(JsonVariantConst j, float speed_frac) {
  for (int i = 0; i < kAxes; ++i) {
    float t = j[i].as<float>();
    ax[i]->setSpeedInHz(cfg::MAX_SPEED[i] * speed_frac * cfg::STEPS_PER_UNIT[i]);
    ax[i]->setAcceleration(cfg::MAX_ACCEL[i] * speed_frac * cfg::STEPS_PER_UNIT[i]);
    ax[i]->moveTo(lroundf(t * cfg::STEPS_PER_UNIT[i]));
  }
  io.digitalWrite(cfg::BEACON, HIGH);
}

static void servo_goal(uint16_t pos, uint16_t torque_pct) {   // Feetech SCS protocol: write goal position (0x2A)
  uint8_t id = 1, p[] = {0x2A, uint8_t(pos & 0xFF), uint8_t(pos >> 8), 0, 0, 0xE8, 0x03};   // 1000 step/s
  uint8_t len = sizeof p + 2, sum = id + len + 0x03;
  for (uint8_t b : p) sum += b;
  SERVO.write(0xFF); SERVO.write(0xFF); SERVO.write(id); SERVO.write(len); SERVO.write(0x03);
  SERVO.write(p, sizeof p); SERVO.write(uint8_t(~sum));
  (void)torque_pct;   // torque limit (0x30) is set once at boot to 50 % (WIRING.md)
}

// ---------- incoming ----------
static void handle(const std::string& line) {
  std::string json;
  if (!unseal(line, json)) { reply(0, false, Err::E09_BAD_FRAME); return; }
  JsonDocument d;
  if (deserializeJson(d, json)) { reply(0, false, Err::E09_BAD_FRAME); return; }
  uint32_t seq = d["seq"] | 0, now = millis();
  const char* c = d["cmd"] | "";
  bool estop = digitalRead(cfg::ESTOP_SENSE) == HIGH;
  sup.heartbeat(now);                                // any valid frame counts as a heartbeat
  if (!strcmp(c, "hello")) { reply(seq, true); status(); }
  else if (!strcmp(c, "heartbeat")) { /* already noted */ }
  else if (!strcmp(c, "get_status")) status();
  else if (!strcmp(c, "home")) { reply(seq, true); home_axes(); status(); }
  else if (!strcmp(c, "permit")) {
    const char* z = d["zone"] | "outside";
    Zone zone = !strcmp(z, "h2s") ? ZONE_H2S : !strcmp(z, "ender") ? ZONE_ENDER : ZONE_OUTSIDE;
    sup.grant_permit(zone, now, d["ms"] | 0);
    reply(seq, true);
  }
  else if (!strcmp(c, "keepout")) { sup.set_keepout(d["x_min"] | 0.0f, d["x_max"] | 0.0f); reply(seq, true); }
  else if (!strcmp(c, "move")) {
    sup.set_x_now(enc_unit[0]);
    float t[kAxes];
    for (int i = 0; i < kAxes; ++i) t[i] = d["j"][i] | NAN;
    const char* z = d["zone"] | "outside";
    Zone zone = !strcmp(z, "h2s") ? ZONE_H2S : !strcmp(z, "ender") ? ZONE_ENDER : ZONE_OUTSIDE;
    Err why = Err::NONE;
    float v = constrain(d["v"] | 0.5f, 0.05f, 1.0f);
    if (sup.request_move(t, zone, now, why)) { start_move(d["j"], v); reply(seq, true); }
    else reply(seq, false, why);
  }
  else if (!strcmp(c, "grip")) {
    if (sup.state() == State::IDLE || sup.state() == State::RUNNING) { servo_goal(d["pos"] | 2048, d["torque"] | 50); reply(seq, true); }
    else reply(seq, false, Err::E06_INTERLOCK);
  }
  else if (!strcmp(c, "pause")) { sup.pause(); all_stop(false); reply(seq, true); }
  else if (!strcmp(c, "halt")) { all_stop(false); sup.move_done(); reply(seq, true); }
  else if (!strcmp(c, "reset")) { reply(seq, sup.reset(estop)); }
  else reply(seq, false, Err::E09_BAD_FRAME);
}

void setup() {
  Serial.begin(115200);
  pinMode(cfg::ESTOP_SENSE, INPUT_PULLUP);
  pinMode(cfg::SSI_CLK, OUTPUT); digitalWrite(cfg::SSI_CLK, HIGH);
  pinMode(cfg::SSI_DATA, INPUT);
  for (uint8_t cs : cfg::ENC_CS) { pinMode(cs, OUTPUT); digitalWrite(cs, HIGH); }
  Wire.begin(cfg::I2C_SDA, cfg::I2C_SCL, 400000);
  io.begin_I2C(0x20);
  for (uint8_t p : cfg::SW_HOME) io.pinMode(p, INPUT_PULLUP);
  io.pinMode(cfg::BEACON, OUTPUT); io.pinMode(cfg::BUZZER, OUTPUT); io.pinMode(cfg::BREAKAWAY, INPUT_PULLUP);
  adc.begin(0x48);
  TMC.begin(115200, SERIAL_8N1, cfg::TMC_RX, cfg::TMC_TX);
  for (uint8_t a = 0; a < 4; ++a) {
    drv[a] = new TMC2209Stepper(&TMC, 0.11f, a);
    drv[a]->begin(); drv[a]->toff(4); drv[a]->microsteps(cfg::MICROSTEPS);
    drv[a]->rms_current(cfg::RUN_CURRENT_MA[a], float(cfg::HOLD_CURRENT_MA) / cfg::RUN_CURRENT_MA[a]);
    drv[a]->pwm_autoscale(true);                               // StealthChop: quiet at night
  }
  SERVO.begin(1000000, SERIAL_8N1, cfg::SERVO_RX, cfg::SERVO_TX);
  engine.init();
  for (int i = 0; i < kAxes; ++i) {
    ax[i] = engine.stepperConnectToPin(cfg::STEP[i]);
    ax[i]->setDirectionPin(cfg::DIR[i]);
    ax[i]->setEnablePin(cfg::EN, true);
    ax[i]->setAutoEnable(false);
  }
  digitalWrite(cfg::EN, LOW);
  read_encoders();
  sup.boot_done();
}

void loop() {
  static uint32_t last_ctl = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n') { handle(std::string(rx.c_str())); rx = ""; }
    else if (rx.length() < kMaxLine) rx += ch;
    else rx = "";                                              // over-long line: drop it (E09 on next)
  }
  uint32_t now = millis();
  if (micros() - last_ctl >= cfg::CONTROL_PERIOD_US) {
    last_ctl = micros();
    read_encoders();
    bool estop = digitalRead(cfg::ESTOP_SENSE) == HIGH;
    bool breakaway = io.digitalRead(cfg::BREAKAWAY) == HIGH;
    float c[kAxes];
    for (int i = 0; i < kAxes; ++i) c[i] = cmd_unit(i);
    if (sup.tick(now, estop, breakaway) || sup.check_following(c, enc_unit)) all_stop(true);
    if (sup.state() == State::RUNNING) {
      bool busy = false;
      for (int i = 0; i < kAxes; ++i) busy |= ax[i]->isRunning();
      if (!busy) { sup.move_done(); io.digitalWrite(cfg::BEACON, LOW); }
    }
  }
  if (now - last_status >= cfg::STATUS_PERIOD_MS) { last_status = now; status(); }
}
