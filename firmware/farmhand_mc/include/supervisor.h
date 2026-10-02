// Safety state machine for the motion controller. Portable C++, host-tested.
// Rules: SAFETY.md H8-H11, H17-H20; contract ARCHITECTURE.md D7.
#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>
#include "protocol.h"

namespace fh {

constexpr int kAxes = 5;                 // X, Z, J1, J2, W
enum Zone : uint8_t { ZONE_OUTSIDE = 0, ZONE_H2S = 1, ZONE_ENDER = 2 };

struct Limits {
  float lo[kAxes] = {0, 0, -150, -145, -180};      // mm, mm, deg, deg, deg
  float hi[kAxes] = {1300, 900, 150, 145, 180};
  float follow_err[kAxes] = {3.0f, 2.0f, 0.6f, 0.8f, 1.5f};   // max |cmd - encoder| before E04
};

class Supervisor {
 public:
  static constexpr uint32_t kWatchdogMs = 500;    // no heartbeat -> controlled stop (H8)
  static constexpr uint32_t kMaxLeaseMs = 5000;   // permit lease ceiling (D7)

  State state() const { return st_; }
  Err error() const { return err_; }
  bool motors_allowed() const { return st_ == State::RUNNING || st_ == State::HOMING; }

  void boot_done() { if (st_ == State::BOOT) st_ = State::UNHOMED; }
  void heartbeat(uint32_t now) { last_hb_ = now; hb_seen_ = true; }

  // Called every control tick. Returns true if motion must stop NOW.
  bool tick(uint32_t now, bool estop_pressed, bool driver_alarm) {
    if (estop_pressed) { if (st_ != State::ESTOP) latch(State::ESTOP, Err::E01_ESTOP); return true; }
    if (driver_alarm && st_ != State::FAULT && st_ != State::ESTOP) { latch(State::FAULT, Err::E07_DRIVER); return true; }
    if ((st_ == State::RUNNING || st_ == State::HOMING) && (!hb_seen_ || now - last_hb_ > kWatchdogMs)) {
      latch(State::FAULT, Err::E02_WATCHDOG); return true;
    }
    if (zone_ != ZONE_OUTSIDE && st_ == State::RUNNING && now >= lease_until_) {
      latch(State::FAULT, Err::E06_INTERLOCK); return true;    // permit expired while inside a printer
    }
    return st_ == State::FAULT || st_ == State::ESTOP;
  }

  void grant_permit(Zone z, uint32_t now, uint32_t ms) {
    permit_zone_ = z;
    lease_until_ = now + (ms > kMaxLeaseMs ? kMaxLeaseMs : ms);
  }

  // Validate a move request. Fills err on refusal.
  bool request_move(const float target[kAxes], Zone z, uint32_t now, Err& why) {
    if (st_ == State::UNHOMED) { why = Err::E08_UNHOMED; return false; }
    if (st_ != State::IDLE && st_ != State::RUNNING) { why = (st_ == State::ESTOP) ? Err::E01_ESTOP : Err::E06_INTERLOCK; return false; }
    for (int i = 0; i < kAxes; ++i)
      if (!(target[i] >= lim_.lo[i] && target[i] <= lim_.hi[i])) { why = Err::E10_RANGE; return false; }
    if (z != ZONE_OUTSIDE && (permit_zone_ != z || now >= lease_until_)) { why = Err::E06_INTERLOCK; return false; }
    if (!hb_seen_ || now - last_hb_ > kWatchdogMs) { why = Err::E02_WATCHDOG; return false; }
    zone_ = z;
    st_ = State::RUNNING;
    return true;
  }
  void move_done() { if (st_ == State::RUNNING) { st_ = State::IDLE; zone_ = ZONE_OUTSIDE; } }
  bool inside_printer() const { return zone_ != ZONE_OUTSIDE; }

  void start_homing() { if (st_ == State::UNHOMED || st_ == State::IDLE) st_ = State::HOMING; }
  void homing_done(bool ok) { if (st_ == State::HOMING) { if (ok) st_ = State::IDLE; else latch(State::FAULT, Err::E03_LIMIT); } }

  void pause() { if (st_ == State::RUNNING) st_ = State::PAUSED; }
  void resume() { if (st_ == State::PAUSED) st_ = State::RUNNING; }

  // Following error check: encoder vs commanded, per axis (H9, D205).
  bool check_following(const float cmd[kAxes], const float meas[kAxes]) {
    if (!motors_allowed()) return false;
    for (int i = 0; i < kAxes; ++i)
      if (std::fabs(cmd[i] - meas[i]) > lim_.follow_err[i]) { latch(State::FAULT, Err::E04_FOLLOWING); return true; }
    return false;
  }

  // reset only clears a latched fault when the cause is gone; always forces a re-home.
  bool reset(bool estop_pressed) {
    if (estop_pressed) return false;
    if (st_ == State::FAULT || st_ == State::ESTOP) { st_ = State::UNHOMED; err_ = Err::NONE; zone_ = ZONE_OUTSIDE; return true; }
    return false;
  }

  Limits& limits() { return lim_; }

 private:
  void latch(State s, Err e) { st_ = s; err_ = e; }
  State st_ = State::BOOT;
  Err err_ = Err::NONE;
  uint32_t last_hb_ = 0, lease_until_ = 0;
  bool hb_seen_ = false;
  Zone permit_zone_ = ZONE_OUTSIDE, zone_ = ZONE_OUTSIDE;
  Limits lim_;
};

}  // namespace fh
