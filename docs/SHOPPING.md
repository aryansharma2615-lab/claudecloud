# FarmHand — Shopping (electronics, software, safety side) — 2026-10-02

Prices are **estimates in CAD, not checked at checkout** — verify each before ordering. Robot hardware is Prompt A's list.

## Phase 2 — printers online (buy now)
| Item | Why | Est. CAD | Where |
|---|---|---|---|
| USB-C → USB-A **data** cable, 1–2 m (e.g. Anker) | Ender ↔ PC serial; charge-only cables are why "nothing happened" | 15 | Amazon.ca |
| Logitech C920 (or C922) webcam | Ender view + Obico + bed-clear check | 90 | Amazon.ca / Best Buy |
| Pushover app (iOS) | Emergency-priority alerts | 7 | [pushover.net](https://pushover.net) |
| Tailscale (Personal) | Funnel tunnel | 0 | [tailscale.com](https://tailscale.com) |
| OctoPrint, Python 3.12, WinSW, OpenCV | Software | 0 | open source |
| **Phase 2 subtotal** | | **≈ 112** | |

## Phase 3 — safety layer (before any unattended run)
| Item | Why | Est. CAD | Link |
|---|---|---|---|
| System Sensor 4WTR-B 4-wire smoke detector w/ relay (12 V) | Smoke → dry contact | 110 | [System Sensor](https://www.systemsensor.com) via electrical supplier |
| System Sensor 5601P heat detector (57 °C fixed + rate-of-rise, passive) | Heat → dry contact, no power | 45 | same |
| 12 V 2 A power supply + DIN terminal block | Powers detector + latch | 25 | Amazon.ca |
| 12 V DPDT relay module + NC reset button + enclosure | Hardware latch | 30 | Amazon.ca |
| Digital Loggers IoT Relay II ×2 | Plug-in mains cut driven by low-voltage signal (one per printer) | 110 | [dlidirect.com](https://dlidirect.com) / Amazon.ca |
| Shelly Plug US (Gen 3/4) ×2 | Local-API power monitoring + 2nd software cut | 70 | [shelly.com](https://www.shelly.com) |
| ESP32 dev board | Reads latch aux + 12 V rail for supervisor | 15 | Amazon.ca |
| E-stop mushroom button, NC, twist-release + box | Hardwired robot stop | 30 | Amazon.ca |
| Automatic fire extinguisher (thermal-trigger ball/tube) | Above the open-frame Ender | 80 | Amazon.ca |
| ABC 5 lb extinguisher | Human response | 60 | Home Depot |
| UPS ~600 VA (APC BE600M1) | PC + router ride-through | 110 | Best Buy |
| **Phase 3 subtotal** | | **≈ 685** | |

## Phase 4 — autonomy
| Item | Why | Est. CAD |
|---|---|---|
| Spare router / VLAN switch for farm segment (if Q5 says needed) | Isolate printers (Developer Mode has no auth beyond the access code) | 60 |
| Extra H2S build plate ×1 | Plate swapping prep | 70 |
| **Phase 4 subtotal** | | **≈ 130** |

## Phase 5 — robot vision (electronics only)
| Item | Est. CAD |
|---|---|
| Overhead camera (2nd C920 or 4K USB) | 90 |
| Wrist camera (small USB global-shutter, Arducam class) | 80 |
| AprilTag prints + acrylic mounts | 10 |
| **Phase 5 subtotal** | **≈ 180** |

## Total (this list): **≈ CAD 1,107** (Phase 2 ≈ 112 · Phase 3 ≈ 685 · Phase 4 ≈ 130 · Phase 5 ≈ 180)
