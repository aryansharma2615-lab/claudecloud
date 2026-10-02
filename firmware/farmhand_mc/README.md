# FarmHand motion controller (ESP32-S3)

- `include/protocol.h` — JSON-lines + CRC-16 framing (mirrors `farm/robot_link.py`).
- `include/supervisor.h` — safety state machine: 500 ms watchdog, E-stop latch, 5 s permit lease for
  entering a printer, soft limits, following-error fault, reset forces re-home.
- `src/main.cpp` — FastAccelStepper on 5 axes, MT6701 SSI encoders, homing (switch + absolute encoder),
  TMC2209 currents over UART, STS3215 gripper, 5 Hz status.
- Commands: `hello`, `heartbeat`, `get_status`, `home`, `permit {zone, ms}`, `move {j:[x,z,j1,j2,w], v, zone}`,
  `grip {pos, torque}`, `keepout {x_min, x_max}` (D248: rail keep-out while the H2S door sweeps the rail), `pause`, `halt`, `reset`.

**Tested:** `g++ -std=c++17 -Iinclude test/host_test.cpp -o /tmp/t && /tmp/t` (protocol + every supervisor rule)
and `pytest tests/test_robot_link.py` (PC framing matches).
**Not yet compiled for the ESP32:** the cloud sandbox blocked the PlatformIO toolchain download. First thing on
your PC: `pio run` in this folder, then fix whatever library API drift shows up (FastAccelStepper / TMCStepper versions).
**Bench order:** one motor + one encoder on the desk → check direction and `STEPS_PER_UNIT` → following-error trip by
holding the shaft → E-stop cuts the motor → then the full robot.
