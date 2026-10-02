# OneShot Arm v5 — wiring + bring-up (ESP32-CAM + UNO, no servo board)

Diagram: [wiring.svg](wiring.svg). Parts are all from your inventory (Mem0): UNO R3 (Elegoo kit), ESP32-CAM + MB
board, 3 × SG90, 28BYJ-48 + ULN2003, breadboard + jumpers, resistors, 1N4007s. From the v5 buy list: 5 V 4 A supply,
1000 µF capacitor, 22 mm E-stop. **Do not** power servos from the UNO 5V pin or the MB-V2 breadboard module (700 mA):
3 stalled SG90s pull ~2 A and the ESP32-CAM browns out (reboots) on any dip.

## Why two boards
The ESP32-CAM's camera uses almost every pin; only ~6 are free and the arm needs 7 (3 servo signals + 4 stepper
inputs). So the **UNO drives the motors** (its Servo library makes the servo pulses itself, no PCA9685 servo board
needed) and the **ESP32-CAM is the camera + Wi-Fi link**, passing text commands to the UNO over a serial wire.

## Connections
| From | To | Why |
|---|---|---|
| PSU +5V | E-stop (NC) in → out → **motor rail** (breadboard red rail) | pressing the E-stop kills every motor, camera keeps working |
| PSU +5V (before the E-stop) | ESP32-CAM 5V | camera/Wi-Fi always on |
| PSU − | **common GND** (breadboard blue rail) | everything shares ground or serial/servo signals don't work |
| 1000 µF cap | + motor rail, − GND (stripe = −) | absorbs servo current spikes |
| 3 × SG90 red / brown | motor rail / GND | |
| SG90 orange (signal) | shoulder **D9**, elbow **D10**, gripper **D11** | |
| ULN2003 + / − | motor rail / GND | |
| ULN2003 IN1–IN4 | **D4, D5, D6, D7** | |
| Motor rail → 10 kΩ → **D2**, and D2 → 100 kΩ → GND | rail sense: UNO knows the E-stop is pressed | |
| Door button (kit) | **D3** ↔ GND. No button? Put a jumper wire from D3 to GND (open D3 = "door open" = arm refuses to move) | interlock |
| ESP32-CAM **GPIO14** | UNO **D0 (RX)** | ESP → UNO commands (3.3 V is enough for the UNO to read HIGH) |
| UNO **D1 (TX)** → 1 kΩ → ESP32-CAM **GPIO15**, and GPIO15 → 2 kΩ → GND | UNO → ESP replies; the divider turns 5 V into 3.3 V so the ESP pin isn't damaged | |
| UNO USB | Mac | power for the UNO + uploads |
| UNO GND, ESP32-CAM GND | common GND | |

## Flash order (today)
1. **UNO:** Arduino IDE → open `uno_arm/uno_arm.ino` → board "Arduino Uno" → upload (unplug the GPIO14→D0 wire first).
   Serial Monitor 115200, type `S` → `OK S 0.0 0.0 0.0 0 rail door_closed idle`.
2. **ESP32-CAM:** IDE → Boards Manager → "esp32 by Espressif" → board **AI Thinker ESP32-CAM**. Copy
   `esp32cam_bridge/secrets.h.example` → `secrets.h`, put your 2.4 GHz Wi-Fi + a key. Plug the ESP32-CAM into the MB
   board, upload, open Serial Monitor: it prints its IP. Then take it off the MB and wire it as above
   (later uploads: Tools → Port → "oneshot" network port, password = your key).
3. **Mac:** `cd oneshot_v5/mac && export ONESHOT_HOST=oneshot.local ONESHOT_KEY=<key>` →
   `python oneshot.py status` → `python oneshot.py look test.jpg`.
4. **Hook me up:** `pip install fastmcp` → `claude mcp add oneshot -e ONESHOT_HOST=oneshot.local -e ONESHOT_KEY=<key> -- python $(pwd)/oneshot_mcp.py`.
   Then in Claude Code / Cowork: "look at the table and pick up the red cube".

## Calibrate (10 min, arm unloaded, E-stop in reach)
1. `raw J 0 0 0 2000` → every joint should sit at its middle. If not, change `SERVO_ZERO_SH/EL` in `uno_arm.ino`
   (servo degrees at joint 0) and re-upload.
2. `move 0 10 0` → shoulder should lift. Wrong way → flip `SIGN_SH`. Same for the elbow with `SIGN_EL`.
3. `grip 0` / `grip 100` → adjust `GRIP_OPEN/CLOSED` so 100 just touches a 20 mm cube (v4 test: contact at ~88°;
   past ~91° the SG90 stalls — stall = heat; don't park it squeezing).
4. Yaw has no home switch on v5: turn the turret to straight-ahead by hand with power off, then `zero`.

## Safety
- The E-stop cuts motor power in hardware; the UNO also stops and detaches servos when it sees the rail drop (D2).
- The ESP32 bridge sends **stop** if the Mac goes quiet for 3 s in the middle of a move (dead-man), and every web
  request needs your key. Keep it on your home Wi-Fi only.
- 1N4007 not needed: the ULN2003 has built-in flyback diodes for the stepper coils.
