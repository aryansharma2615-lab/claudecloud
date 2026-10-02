// Pins and mechanics. Pin map = docs/WIRING.md. Ratios = docs/BOM.md (lean) + cad/params.py.
#pragma once
#include <cstdint>

namespace cfg {
// axis order everywhere: X, Z, J1, J2, W
constexpr uint8_t STEP[5] = {4, 6, 15, 17, 8};
constexpr uint8_t DIR[5] = {5, 7, 16, 18, 9};
constexpr uint8_t EN = 10;                       // shared, active low
constexpr uint8_t TMC_TX = 11, TMC_RX = 12;
constexpr uint8_t SSI_CLK = 13, SSI_DATA = 14;
constexpr uint8_t ENC_CS[5] = {39, 38, 1, 2, 21};  // X idler, Z screw, J1 out, J2 out, W out
constexpr uint8_t I2C_SDA = 40, I2C_SCL = 41;
constexpr uint8_t HX_DOUT = 42, HX_SCK = 47;
constexpr uint8_t ESTOP_SENSE = 48;              // HIGH = pressed (NC contact opens, pull-up)
constexpr uint8_t SERVO_TX = 43, SERVO_RX = 44;

// MCP23017 pins
constexpr uint8_t SW_HOME[5] = {0, 2, 4, 5, 6};  // X min, Z min, J1, J2, W(index)  (X max = 1, Z max = 3)
constexpr uint8_t BEACON = 8, BUZZER = 9, BREAKAWAY = 10;

constexpr float MICROSTEPS = 16, FULL_STEPS = 200;
// steps per unit: X mm (GT2 20T = 40 mm/rev), Z mm (T8x2 = 2 mm/rev), J1 deg (1:16), J2 deg (1:8), W deg (1:4)
constexpr float STEPS_PER_UNIT[5] = {MICROSTEPS * FULL_STEPS / 40.0f, MICROSTEPS * FULL_STEPS / 2.0f,
                                     MICROSTEPS * FULL_STEPS * 16 / 360.0f, MICROSTEPS * FULL_STEPS * 8 / 360.0f,
                                     MICROSTEPS * FULL_STEPS * 4 / 360.0f};
// encoder units per revolution of the encoder magnet (X idler is 20T GT2 = 40 mm; Z on the screw = 2 mm)
constexpr float ENC_UNITS_PER_REV[5] = {40.0f, 2.0f, 360.0f, 360.0f, 360.0f};
constexpr bool ENC_MULTITURN[5] = {true, true, false, false, false};   // X/Z encoders count turns in firmware
constexpr float MAX_SPEED[5] = {500, 20, 90, 120, 180};     // unit/s (lean BOM speeds)
constexpr float MAX_ACCEL[5] = {500, 40, 120, 200, 400};    // unit/s^2
constexpr float HOME_SPEED[5] = {60, 8, 15, 15, 30};
constexpr uint16_t RUN_CURRENT_MA[5] = {1200, 1000, 1400, 1200, 1000};
constexpr uint16_t HOLD_CURRENT_MA = 300;        // no gravity on revolute joints; Z self-locks
constexpr uint32_t STATUS_PERIOD_MS = 200;       // 5 Hz (D7)
constexpr uint32_t CONTROL_PERIOD_US = 1000;     // 1 kHz encoder + safety loop
}  // namespace cfg
