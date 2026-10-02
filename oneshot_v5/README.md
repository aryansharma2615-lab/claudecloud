# OneShot Arm v5 — control stack (ESP32-CAM + UNO, Claude-controlled)

- `uno_arm/uno_arm.ino` — UNO drives 3 × SG90 (D9/D10/D11) + 28BYJ-48 yaw (ULN2003 on D4–D7); smooth min-jerk moves,
  joint limits, E-stop rail sense (D2), door interlock (D3). Text protocol: `P S J G H Z X` (see the file header).
- `esp32cam_bridge/` — ESP32-CAM: `/capture` JPEG, `/stream` MJPEG, `/cmd` → UNO serial, API key, 3 s dead-man stop, OTA.
- `mac/oneshot.py` — CLI/library; `mac/oneshot_mcp.py` — MCP server (look, move, grip, home, stop, status) so Claude
  sees and moves the arm.
- [WIRING.md](WIRING.md) + [wiring.svg](wiring.svg) — every wire, flash order, calibration, safety.

**Not compiled yet** (the cloud session couldn't download the Arduino cores) — first upload on the Mac will show any
library-version errors. If you'd rather keep your v5.2 UNO firmware (`~/Claude/OneShot/v5/firmware/oneshot_v5_2/`,
with the `L r z` straight-line command), flash that instead: the bridge passes any text line through unchanged, and
`oneshot.py raw "L 120 30"` reaches it. Then align its reply words (`OK`, `DONE`, `ERR`) with the bridge's
`unoTalk()` end markers.
