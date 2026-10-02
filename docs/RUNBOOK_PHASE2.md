# Phase 2 runbook — printers online (run ON the Windows 10 farm PC)

Each step has a ✅ check. Stop at the first ❌ and paste me the output.
Paths assume `C:\FarmHand\app` (this repo) and `C:\FarmHand\data`.

## 0 · Software on the PC (≈ 20 min)
1. Python 3.12 from python.org (tick "Add to PATH"). Git for Windows. ffmpeg: `winget install Gyan.FFmpeg`.
2. ```
   git clone https://github.com/aryansharma2615-lab/claudecloud C:\FarmHand\app
   cd C:\FarmHand\app
   git checkout claude/tender-wright-ifxm96
   py -3.12 -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   .venv\Scripts\python -m pytest -q
   copy .env.example .env
   ```
   ✅ `34 passed`.

## 1 · Ender over USB-C (≈ 30 min)
1. Use a **data** USB-C cable (a charge-only cable is the #1 reason "nothing happened").
2. Install the CH340 driver: [WCH CH341SER](https://www.wch-ic.com/downloads/CH341SER_EXE.html) → INSTALL.
3. Plug in, printer ON. Device Manager → Ports → ✅ `USB-SERIAL CH340 (COMx)`.
4. Install OctoPrint: [octoprint.org/download](https://octoprint.org/download/) (Windows installer, runs as a service). Open `http://127.0.0.1:5000`, finish the wizard.
5. Connection panel: port COMx, baud **AUTO** (stock firmware = 115200) → Connect. ✅ temperatures appear.
6. OctoPrint → Settings → Access Control: create user `farm` with **PRINT, STATUS, FILES_UPLOAD, WEBCAM** and **not** CONTROL. Settings → Application Keys → key for `farm` → paste into `.env` as `OCTOPRINT_API_KEY`.
7. Plug the C920 in, aim it at the Ender bed. `ENDER_CAMERA_INDEX=0` (try 1 if the laptop cam answers).
8. In OctoPrint's terminal tab: `G28` (home). ✅ printer homes.
9. Slice a ~10-min test (20 mm cube, 2 walls) to `.gcode`.

## 2 · H2S LAN-only + Developer Mode (≈ 15 min) — **your decision, you lose Bambu Handy/cloud**
1. Printer screen: Settings → firmware version → **write it down** (Gate 1 Q1). Turn **auto-update OFF**.
2. Settings → WLAN/Network → **LAN Only** ON → **Developer Mode** ON → **LAN Only Liveview** ON.
3. Note: IP address, Access Code, Serial (Settings → Device). Put them in `.env`.
4. In your router, give the H2S a **reserved IP** (DHCP reservation) so it never moves.

## 3 · Dry run, then real status (≈ 10 min)
```
.venv\Scripts\python -m farm.cli status          # FARM_DRY_RUN=1 → fake printers
```
Then set `FARM_DRY_RUN=0` in `.env`:
```
.venv\Scripts\python -m farm.cli status
```
✅ both printers show a real state + temperatures; AMS trays listed for the H2S.

## 4 · Bed references + library (≈ 10 min)
1. Both beds **empty**, plates seated:
   ```
   .venv\Scripts\python -m farm.cli capture-reference h2s
   .venv\Scripts\python -m farm.cli capture-reference ender
   ```
   Open `C:\FarmHand\data\vision\*_empty.jpg`, read the pixel box around the bed in Paint (bottom-left shows x,y), then
   `python -m farm.cli set-roi h2s X Y W H` (same for ender).
2. Add the test files (H2S: in Bambu Studio "Export plate sliced file" → `.gcode.3mf`):
   ```
   .venv\Scripts\python -m farm.cli library-add ender C:\prints\cube.gcode --name "Test cube"
   .venv\Scripts\python -m farm.cli library-add h2s C:\prints\cube.gcode.3mf --name "Test cube"
   ```

## 5 · Local MCP test (no internet yet)
`.venv\Scripts\python -m farm.mcp_server` → ✅ "Uvicorn running on http://127.0.0.1:8765".
Leave it; in Claude Desktop/Code on the same PC you can add `http://127.0.0.1:8765/mcp` to try tools.
**10-min Ender test print here**, start_print → confirm. Watch it the whole time.

## 6 · Go public safely (≈ 20 min)
1. Install [Tailscale](https://tailscale.com/download/windows), sign in. Admin console → DNS → enable **MagicDNS** + **HTTPS certificates**; Access controls → allow **Funnel** for this machine.
2. `tailscale funnel --bg 8765` → ✅ prints `https://<pc>.<tailnet>.ts.net`. Put it in `FARM_PUBLIC_URL`.
3. GitHub → Settings → Developer settings → OAuth Apps → New: homepage = that URL, callback = `<URL>/auth/callback`. Copy client ID/secret into `.env`. Set `FARM_ALLOWED_GITHUB_LOGIN` = your GitHub username, and `FARM_JWT_SIGNING_KEY`.
4. Install as a service: download WinSW-x64.exe to `deploy\`, rename `farm-server.exe`, then (admin prompt) `deploy\farm-server.exe install` and `start`.
5. claude.ai → Settings → Connectors → Add custom connector → `<URL>/mcp` → sign in with GitHub.
6. In the connector's tool settings set **`confirm_action` → "Needs approval"** (every start/resume/cancel then needs your tap, even if Claude misbehaves). Leave `stop_all` and `pause` on "Always allow".
7. From a **different** GitHub account (or a private window) try connecting → ✅ tools refuse.

## 7 · Record real fixtures (helps the next phases)
Send me: the output of step 3 status, and OctoPrint `GET /api/printer` + `/api/job` JSON during a print. I'll replace the synthetic fixtures. Also: does anything in the H2S report change when you open the door? (Gate 1 Q2)

## GATE 2 test
From your phone's Claude app: **"what's printing?"** → both printers' status + photos.

## Safety while in Phase 2
No unattended printing yet: the smoke/heat cutoff is Phase 3. Every start preflight says so.
