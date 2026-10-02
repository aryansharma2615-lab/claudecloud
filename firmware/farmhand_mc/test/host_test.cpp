// Host unit tests for protocol.h + supervisor.h:  g++ -std=c++17 -Iinclude test/host_test.cpp -o /tmp/t && /tmp/t
#include <cassert>
#include <cstdio>
#include "protocol.h"
#include "supervisor.h"
using namespace fh;

int main() {
  // CRC-16/CCITT-FALSE check value
  assert(crc16("123456789", 9) == 0x29B1);
  std::string line = seal("{\"seq\":1,\"cmd\":\"hello\""), json;
  assert(unseal(line, json) && json == "{\"seq\":1,\"cmd\":\"hello\"}");
  std::string bad = line; bad[8] = 'X';
  assert(!unseal(bad, json));
  assert(!unseal("{\"seq\":1}", json));

  Supervisor s;
  float home[kAxes] = {100, 100, 0, 0, 0};
  Err e;
  assert(!s.request_move(home, ZONE_OUTSIDE, 0, e));          // BOOT
  s.boot_done();
  assert(!s.request_move(home, ZONE_OUTSIDE, 0, e) && e == Err::E08_UNHOMED);
  s.start_homing(); s.heartbeat(0); s.homing_done(true);
  assert(s.state() == State::IDLE);
  s.heartbeat(1000);
  assert(s.request_move(home, ZONE_OUTSIDE, 1000, e));        // outside: no permit needed
  s.move_done();
  assert(!s.request_move(home, ZONE_H2S, 1100, e) && e == Err::E06_INTERLOCK);   // inside needs a permit
  s.grant_permit(ZONE_H2S, 1100, 99999);                      // lease clamped to 5 s
  assert(!s.request_move(home, ZONE_ENDER, 1100, e));         // wrong printer
  assert(s.request_move(home, ZONE_H2S, 1100, e) && s.inside_printer());
  s.heartbeat(5900);
  assert(!s.tick(5900, false, false));
  s.heartbeat(6200);
  assert(s.tick(6200, false, false) && s.error() == Err::E06_INTERLOCK);   // lease expired inside
  assert(s.reset(false) && s.state() == State::UNHOMED);       // reset forces re-home
  s.start_homing(); s.homing_done(true);
  s.heartbeat(7000);
  assert(s.request_move(home, ZONE_OUTSIDE, 7000, e));
  assert(s.tick(7600, false, false) && s.error() == Err::E02_WATCHDOG);    // no heartbeat for 600 ms
  s.reset(false); s.start_homing(); s.homing_done(true); s.heartbeat(8000);
  float far[kAxes] = {2000, 0, 0, 0, 0};
  assert(!s.request_move(far, ZONE_OUTSIDE, 8000, e) && e == Err::E10_RANGE);
  assert(s.request_move(home, ZONE_OUTSIDE, 8000, e));
  float meas[kAxes] = {100, 100, 1.0f, 0, 0};
  assert(s.check_following(home, meas) && s.error() == Err::E04_FOLLOWING);  // 1° > 0.6° on J1
  assert(s.tick(8001, true, false) && s.state() == State::ESTOP);
  assert(!s.reset(true));                                      // can't reset while pressed
  assert(s.reset(false));
  // D248 keep-out: door sweeping the rail line between X 200 and 500
  s.start_homing(); s.homing_done(true); s.heartbeat(9000);
  s.set_keepout(200, 500); s.set_x_now(100);
  float across[kAxes] = {700, 100, 0, 0, 0};
  assert(!s.request_move(across, ZONE_OUTSIDE, 9000, e) && e == Err::E06_INTERLOCK);   // would drive through the door
  float near_[kAxes] = {150, 100, 0, 0, 0};
  assert(s.request_move(near_, ZONE_OUTSIDE, 9000, e));
  s.move_done(); s.set_keepout(0, 0);
  assert(s.request_move(across, ZONE_OUTSIDE, 9000, e));
  puts("host tests: all passed");
}
