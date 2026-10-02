// FarmHand robot link — framing shared with the farm PC (docs/ARCHITECTURE.md D7).
// Line = JSON object, crc as the LAST key:  {"seq":7,"cmd":"heartbeat","crc":"1A2B"}\n
// crc = CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) of the line with ,"crc":"XXXX" removed.
// Portable C++ (no Arduino) so it is unit-tested on the host: test/host_test.cpp.
#pragma once
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

namespace fh {

constexpr size_t kMaxLine = 512;

inline uint16_t crc16(const char* d, size_t n) {
  uint16_t c = 0xFFFF;
  for (size_t i = 0; i < n; ++i) {
    c ^= static_cast<uint16_t>(static_cast<uint8_t>(d[i])) << 8;
    for (int b = 0; b < 8; ++b) c = (c & 0x8000) ? (c << 1) ^ 0x1021 : (c << 1);
  }
  return c;
}

// body = a JSON object WITHOUT its closing brace, e.g. {"seq":1,"evt":"status"
inline std::string seal(const std::string& body) {
  std::string closed = body + "}";
  char tail[20];
  snprintf(tail, sizeof tail, ",\"crc\":\"%04X\"}", crc16(closed.data(), closed.size()));
  return body + tail;
}

// Returns true and fills `json` (the line without the crc key) when the crc matches.
inline bool unseal(const std::string& line, std::string& json) {
  if (line.size() > kMaxLine) return false;
  const char* key = ",\"crc\":\"";
  size_t p = line.rfind(key);
  if (p == std::string::npos || line.size() < p + 8 + 4 + 2) return false;
  std::string hex = line.substr(p + 8, 4);
  if (line.compare(p + 12, 2, "\"}") != 0) return false;
  char* end = nullptr;
  unsigned long got = strtoul(hex.c_str(), &end, 16);
  if (end != hex.c_str() + 4) return false;
  json = line.substr(0, p) + "}";
  return crc16(json.data(), json.size()) == got;
}

enum class State : uint8_t { BOOT, UNHOMED, HOMING, IDLE, RUNNING, PAUSED, FAULT, ESTOP };
enum class Err : uint8_t { NONE = 0, E01_ESTOP, E02_WATCHDOG, E03_LIMIT, E04_FOLLOWING, E05_HASH,
                           E06_INTERLOCK, E07_DRIVER, E08_UNHOMED, E09_BAD_FRAME, E10_RANGE };

inline const char* state_name(State s) {
  static const char* n[] = {"BOOT", "UNHOMED", "HOMING", "IDLE", "RUNNING", "PAUSED", "FAULT", "ESTOP"};
  return n[static_cast<int>(s)];
}
inline const char* err_name(Err e) {
  static const char* n[] = {"", "E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08", "E09", "E10"};
  return n[static_cast<int>(e)];
}

}  // namespace fh
