# Ender control — today, no H2S needed (≈ 45 min on the Windows PC)

Goal: text Claude "what's the Ender doing?" and start/pause it from your phone.
Easiest: open Claude Code on the PC in `C:\FarmHand\app` and say
*"Read docs/ENDER_NOW.md and walk me through it. Run commands yourself; stop when I need to touch something."*

## 1 · Get the code (5 min)
```
git clone https://github.com/aryansharma2615-lab/claudecloud C:\FarmHand\app
cd C:\FarmHand\app
git checkout claude/tender-wright-ifxm96
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest -q
copy .env.example .env
```
✅ all tests pass. `.env` already says `FARM_PRINTERS=ender`.

## 2 · Prove the USB link (10 min) — the "plugging it in did nothing" fix
1. **Data** USB-C cable, printer ON.
2. Driver: [WCH CH341SER](https://www.wch-ic.com/downloads/CH341SER_EXE.html) → INSTALL.
3. `.venv\Scripts\python -m farm.ender_check`
   ✅ `CH340 found on COMx` · `talks at 115200 baud` · `THERMAL_PROTECTION:1`
   This reads the printer's own firmware report, so we **know** runaway protection is on instead of trusting a forum.

## 3 · OctoPrint (15 min)
Runbook Phase 2 **step 1, items 4–8**: install, connect at the baud from step 2, create user `farm` (PRINT, not CONTROL), API key into `.env`, plug the webcam in.

## 4 · Farm, Ender only (10 min)
1. `.env`: `FARM_DRY_RUN=0`
2. `.venv\Scripts\python -m farm.cli status` → ✅ Ender state + temps.
3. Empty bed: `.venv\Scripts\python -m farm.cli capture-reference ender`
4. `.venv\Scripts\python -m farm.cli library-add ender C:\prints\cube.gcode --name "Test cube"`

## 5 · Phone control
Runbook Phase 2 **steps 5–6** (local test, then Tailscale Funnel + GitHub login + connector).
Then from the Claude app: "what's the Ender doing?" · "start the test cube on the Ender" (you tap approve) · "pause the Ender".

**When the H2S arrives:** set `FARM_PRINTERS=h2s,ender` and do runbook step 2.

**Fallback if software ever can't:** the robot taps the Ender screen (Phase 5) — software first, fingers last.
