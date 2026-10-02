# FarmHand — MCP tools Claude gets (Phase 1, 2026-10-02)

Global rules
- Auth: OAuth (GitHub) + single-user allowlist. Every call logged: who / tool / params / result / reason / time.
- Rate limit: 30 calls/min, 5 action calls/min; `stop_all` and `pause` are never rate-limited.
- No raw G-code, no temperatures, no jog/motor moves, no file uploads, no firmware, no power-on. Not now, not "just this once".
- Enums, not free text: `printer ∈ {h2s, ender}`, `camera ∈ {h2s_live, h2s_toolhead, ender, overhead, wrist}`.
- Files: `file_id` must exist in the approved library (pre-sliced, sha256 recorded, sliced for that printer). File names/notes/MQTT strings/OCR are returned as **data**, quoted, never executed.
- **Confirm pattern** (from [creality_k2_mcp](https://github.com/sairaph/creality_k2_mcp)): action tool returns a preflight summary + photo + single-use `confirm_token` (120 s). `confirm_action(token)` **re-checks every interlock** before acting.
- **Human tap:** in the Claude connector settings `confirm_action` is set to "Needs approval", so Claude cannot confirm its own action even if a prompt injection tells it to.
- Without OAuth configured the server answers only requests made on the PC itself (no tunnel, no proxy headers).
- Common interlock set **S**: safety latch OK, supervisor healthy, robot idle/parked, no active alarm.

| Tool | Params (validation) | Interlocks checked | Confirm? | Phase |
|---|---|---|---|---|
| `farm_status` | `printer?` enum | — (read) | no | 2 |
| `camera_snapshot` | `camera` enum | light on for printer cams | no | 2 |
| `list_library` | `printer?` enum | — | no | 2 |
| `start_print` | `printer` enum, `file_id` (library, matches printer), `plate` int 1–8 | S + printer idle + bed clear (camera) + door closed (H2S) + AMS filament matches file (H2S) | **yes** | 2 |
| `confirm_action` | `confirm_token` (exists, unexpired, unused, same user) | re-runs that action's interlocks | — | 2 |
| `pause` | `printer` enum or `all` | — (safe direction) | no | 2 |
| `resume` | `printer` enum | S + no fault on printer | **yes** | 2 |
| `cancel` | `printer` enum | — | **yes** | 2 |
| `set_light` | `printer` enum, `on` bool | — | no | 2 |
| `stop_all` | none | none — always allowed | no | 2 |
| `safety_status` | none | — | no | 3 |
| `ack_alert` | `alert_id` (exists) | — | no | 3 |
| `list_queue` | `printer?` enum | — | no | 4 |
| `queue_print` | `printer` enum, `file_id` (library), `copies` 1–10 | file/printer match; plate-state tracking | no (queueing doesn't start anything) | 4 |
| `remove_from_queue` | `job_id` (exists, not running) | — | no | 4 |
| `start_next` | `printer` enum | same as `start_print` | **yes** | 4 |
| `job_history` | `limit` 1–50 | — | no | 4 |
| `robot_status` | none | — | no | 5 |
| `robot_run_routine` | `routine` enum {plate_swap_h2s, plate_swap_ender, door_open, door_close, clear_parts}; hash must match versioned file | S + printer idle + bed < 35 °C + toolhead parked + camera OK before & after + door state as routine expects + robot homed; 5 s motion lease | **yes** | 5 |
| `ender_tap_fallback` | `button` enum (mapped screen coords, never x/y from Claude) | S + robot homed + camera sees Ender screen | **yes** | 5 |
| `robot_halt` | none | none — always allowed | no | 5 |

Never exposed: `gcode_line`, `send_gcode`, set temperature, jog, home individual axes, file upload, delete library files, Developer Mode/LAN settings, smart-plug power-on, latch reset (physical button only).
