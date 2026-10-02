"""Ender USB-C check — run BEFORE OctoPrint grabs the port (or with OctoPrint disconnected).

  python -m farm.ender_check            # finds the CH340 port, tries 115200 then 250000

Answers "why did plugging it in do nothing?" step by step, and asks the printer's own
firmware (M115) whether thermal-runaway protection is compiled in.
Read-only: sends only M115 (firmware info). No motion, no heating.
"""
from __future__ import annotations

import sys
import time

CH340_VID = 0x1A86  # WCH, maker of the CH340/CH341 USB-serial chip
BAUDS = (115200, 250000)


def parse_m115(text: str) -> dict:
    """'FIRMWARE_NAME:Marlin ... \\nCap:THERMAL_PROTECTION:1' → fields + capability flags."""
    info: dict = {"caps": {}}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Cap:"):
            parts = line[4:].rsplit(":", 1)
            if len(parts) == 2:
                info["caps"][parts[0]] = parts[1].strip() == "1"
        elif "FIRMWARE_NAME:" in line:
            info["firmware"] = line.split("FIRMWARE_NAME:", 1)[1].split(" SOURCE_CODE_URL")[0].strip()
            if "MACHINE_TYPE:" in line:
                info["machine"] = line.split("MACHINE_TYPE:", 1)[1].split(" EXTRUDER_COUNT")[0].strip()
    return info


def find_ports():
    from serial.tools import list_ports

    ports = list(list_ports.comports())
    ch340 = [p for p in ports if p.vid == CH340_VID]
    return ch340, ports


def ask_m115(port: str, baud: int, wait_s: float = 2.5) -> str:
    import serial

    with serial.Serial(port, baud, timeout=0.5) as s:
        time.sleep(wait_s)          # opening the port can reset the board; let it boot
        s.reset_input_buffer()
        s.write(b"M115\n")
        deadline, buf = time.time() + 4, b""
        while time.time() < deadline:
            buf += s.read(512)
            if b"ok" in buf and b"FIRMWARE_NAME" in buf:
                break
        return buf.decode("ascii", "replace")


def main() -> int:
    try:
        ch340, ports = find_ports()
    except ImportError:
        print("pyserial missing: .venv\\Scripts\\pip install -r requirements.txt")
        return 1
    if not ch340:
        print("❌ No CH340 serial port found.")
        if ports:
            print("   Other ports seen:", ", ".join(f"{p.device} ({p.description})" for p in ports))
        print("   Fix in this order: 1) printer ON  2) a DATA USB-C cable (charge-only cables are common)\n"
              "   3) install the CH341SER driver  4) check Device Manager → Ports (COM & LPT)")
        return 1
    port = ch340[0].device
    print(f"✅ CH340 found on {port}")
    for baud in BAUDS:
        try:
            reply = ask_m115(port, baud)
        except Exception as exc:  # port busy etc.
            print(f"❌ could not open {port}: {exc}\n   Is OctoPrint (or Cura/Pronterface) connected? Disconnect it first.")
            return 1
        info = parse_m115(reply)
        if "firmware" in info:
            print(f"✅ talks at {baud} baud → use this in OctoPrint")
            print(f"   firmware: {info['firmware']}   machine: {info.get('machine', '?')}")
            tp = info["caps"].get("THERMAL_PROTECTION")
            if tp is True:
                print("✅ firmware reports THERMAL_PROTECTION:1 (thermal-runaway protection compiled in)")
            elif tp is False:
                print("⚠️  firmware reports THERMAL_PROTECTION:0 — protection OFF. Do not print unattended; reflash.")
            else:
                print("⚠️  firmware does not report THERMAL_PROTECTION — do the hardware test in SAFETY.md H3")
            return 0
        print(f"…no answer at {baud} baud")
    print("❌ Port opens but firmware never answered. Try another cable/USB port, or power-cycle the printer.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
