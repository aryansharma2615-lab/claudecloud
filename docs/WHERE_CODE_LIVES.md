# FarmHand — Where the code lives (confirmed Phase 1, 2026-10-02)

The prompt's table holds, with three corrections: **(1)** the safety supervisor is its own process/service, not part of the farm server; **(2)** a tiny ESP32 board watches the hardware latch; **(3)** the tunnel is Tailscale Funnel.

| Piece | Language | Runs on | Job | Repo path |
|---|---|---|---|---|
| Robot motion controller | C++ (PlatformIO) | controller board on robot (Prompt A picks; ESP32-S3 / RP2040 fit [FastAccelStepper](https://github.com/gin66/FastAccelStepper)) | steps, encoders, homing, limits, E-stop input, 500 ms watchdog, routine runner | `robot_fw/` |
| Farm server | Python 3.12 | Windows PC, WinSW service, auto-restart, rotating logs | printer drivers, cameras, vision, queue, robot driver, MCP tools, action log | `farm/` |
| Safety supervisor | Python 3.12 (minimal deps) | Windows PC, **separate** WinSW service | watchdogs farm + robot, reads latch/plugs, pauses/halts/alerts | `supervisor/` |
| Latch monitor | C++ (PlatformIO) | ESP32 next to the latch box | reports latch state + 12 V rail over USB serial | `latch_fw/` |
| OctoPrint | off-the-shelf (AGPL, unmodified) | Windows PC service | drives Ender over USB-C serial | config only: `deploy/octoprint/` |
| Obico, Bambuddy (optional) | off-the-shelf (AGPL, unmodified sidecars) | Windows PC | failure detection / H2S farm UI | config only |
| H2S firmware | Bambu | printer | — | firmware version pinned in `deploy/firmware.md` |
| Tunnel | Tailscale | Windows PC service | public HTTPS → farm MCP | `deploy/tailscale.md` |
| Claude | — | Claude app | calls whitelisted tools only | `docs/MCP_TOOLS.md` |

Planned layout:
```
farm/
  printers/  bambu.py  octoprint.py  base.py      # one interface, two drivers
  vision/    bed_clear.py  cameras.py
  queue/     jobs.py  library.py                    # approved pre-sliced files, sha256
  robot/     driver.py  routines/*.json (versioned)
  mcp/       server.py  tools.py  confirm.py  auth.py
  safety/    interlocks.py
  store/     sqlite (status log, action log, queue)
  notify/    pushover.py
supervisor/  main.py
robot_fw/  latch_fw/  deploy/  tests/fixtures/(mqtt, octoprint)  docs/  prompts/
```
Secrets in `.env` (git-ignored). Windows paths via `pathlib`.
