"""Bambu H2S driver: LAN-only + Developer Mode.

Protocol reference (community, not official): https://github.com/Doridian/OpenBambuAPI
MQTT  : TLS 8883, user "bblp", password = LAN access code
        subscribe device/<serial>/report, publish device/<serial>/request
Upload: implicit FTPS 990, same credentials
Camera: RTSPS 322 (needs "LAN Only Liveview" on), one frame grabbed with ffmpeg

Never exposes gcode_line. Commands are built by the pure functions below so they
can be unit-tested without a printer.
"""
from __future__ import annotations

import copy
import ftplib
import hashlib
import json
import socket
import ssl
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from .base import PrinterError, PrinterStatus, State, Tray, clean_text

GCODE_STATE = {
    "IDLE": State.IDLE,
    "PREPARE": State.PREPARING,
    "SLICING": State.PREPARING,
    "RUNNING": State.PRINTING,
    "PAUSE": State.PAUSED,
    "FINISH": State.FINISHED,
    "FAILED": State.FAILED,
}


# ---------- pure helpers (tested with fixtures) ----------

def deep_merge(base: dict, delta: dict) -> dict:
    """Bambu sends partial reports; merge each into the last full picture."""
    out = copy.deepcopy(base)
    for k, v in delta.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _dig(d: dict, dotted: str) -> Any:
    cur: Any = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def parse_report(report: dict, door_field: str = "", printer: str = "h2s") -> PrinterStatus:
    p = report.get("print", {})
    raw_state = str(p.get("gcode_state", "")).upper()
    state = GCODE_STATE.get(raw_state, State.OFFLINE if not p else State.IDLE)
    err_code = p.get("print_error") or 0
    error = f"print_error {err_code:#x}" if isinstance(err_code, int) and err_code else ""
    if error and state in (State.IDLE, State.PREPARING):
        state = State.ERROR  # an error while printing/paused keeps that state, error shown

    trays: list[Tray] = []
    for unit in (p.get("ams") or {}).get("ams", []) or []:
        try:
            ams_id = int(unit.get("id", 0))
        except (TypeError, ValueError):
            continue
        for t in unit.get("tray", []) or []:
            material = clean_text(t.get("tray_type"), 16)
            if not material:
                continue
            try:
                slot = ams_id * 4 + int(t.get("id", 0))
            except (TypeError, ValueError):
                continue
            remain = t.get("remain")
            trays.append(Tray(
                slot=slot,
                material=material.upper(),
                color=clean_text(t.get("tray_color"), 8).upper(),
                remain_pct=remain if isinstance(remain, int) and remain >= 0 else None,
            ))

    door = None
    if door_field:
        v = _dig(report, door_field)
        if isinstance(v, (bool, int)):
            door = bool(v)

    def num(key: str) -> float | None:
        v = p.get(key)
        return float(v) if isinstance(v, (int, float)) else None

    remaining = p.get("mc_remaining_time")
    return PrinterStatus(
        printer=printer,
        state=state,
        job_name=clean_text(p.get("subtask_name")),
        progress_pct=num("mc_percent"),
        remaining_min=int(remaining) if isinstance(remaining, (int, float)) else None,
        nozzle_c=num("nozzle_temper"),
        bed_c=num("bed_temper"),
        chamber_c=num("chamber_temper"),
        door_open=door,
        error=error,
        trays=trays,
    )


def cmd_pushall(seq: int) -> dict:
    return {"pushing": {"sequence_id": str(seq), "command": "pushall"}}


def cmd_print(seq: int, action: str) -> dict:
    if action not in {"pause", "resume", "stop"}:
        raise ValueError(action)
    return {"print": {"sequence_id": str(seq), "command": action}}


def cmd_light(seq: int, on: bool) -> dict:
    return {"system": {
        "sequence_id": str(seq), "command": "ledctrl", "led_node": "chamber_light",
        "led_mode": "on" if on else "off", "led_on_time": 500, "led_off_time": 500,
        "loop_times": 0, "interval_time": 0,
    }}


def cmd_project_file(seq: int, remote_name: str, url: str, md5: str, plate: int,
                     ams_mapping: list[int] | None) -> dict:
    if not 1 <= plate <= 8:
        raise ValueError("plate")
    return {"print": {
        "sequence_id": str(seq), "command": "project_file",
        "param": f"Metadata/plate_{plate}.gcode",
        "project_id": "0", "profile_id": "0", "task_id": "0", "subtask_id": "0",
        "subtask_name": remote_name, "url": url, "md5": md5,
        "timelapse": False, "bed_type": "auto", "bed_levelling": True,
        "flow_cali": True, "vibration_cali": True, "layer_inspect": True,
        "use_ams": bool(ams_mapping), "ams_mapping": ams_mapping or [],
    }}


# ---------- FTPS (implicit TLS, data channel must reuse the TLS session) ----------

class _ImplicitFTPS(ftplib.FTP_TLS):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._sock = None

    @property
    def sock(self):
        return self._sock

    @sock.setter
    def sock(self, value):
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value)
        self._sock = value

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn, server_hostname=self.host,
                                            session=self.sock.session)
        return conn, size


def _lan_tls_context() -> ssl.SSLContext:
    # The printer presents a Bambu-signed cert for its serial, not its IP. It is
    # only reachable on the farm LAN segment, so we accept it without hostname
    # checks. Pinning the cert is a Phase 6 hardening item.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


# ---------- live driver ----------

class BambuPrinter:
    name = "h2s"

    def __init__(self, host: str, serial: str, access_code: str,
                 file_url_template: str, door_field: str = ""):
        if not (host and serial and access_code):
            raise PrinterError("H2S not configured: set BAMBU_HOST, BAMBU_SERIAL, BAMBU_ACCESS_CODE")
        import paho.mqtt.client as mqtt

        self.host, self.serial, self.code = host, serial, access_code
        self.file_url_template = file_url_template
        self.door_field = door_field
        self._report: dict = {}
        self._last_msg = 0.0
        self._seq = 0
        self._lock = threading.Lock()

        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"farmhand-{int(time.time())}")
        c.username_pw_set("bblp", access_code)
        c.tls_set_context(_lan_tls_context())
        c.on_connect = self._on_connect
        c.on_message = self._on_message
        c.reconnect_delay_set(1, 30)
        c.connect_async(host, 8883, keepalive=30)
        c.loop_start()
        self._mqtt = c

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        client.subscribe(f"device/{self.serial}/report")
        self._publish(cmd_pushall(self._next_seq()))

    def _on_message(self, client, userdata, msg):
        try:
            delta = json.loads(msg.payload)
        except (ValueError, UnicodeDecodeError):
            return
        if isinstance(delta, dict):
            with self._lock:
                self._report = deep_merge(self._report, delta)
                self._last_msg = time.monotonic()

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _publish(self, payload: dict) -> None:
        info = self._mqtt.publish(f"device/{self.serial}/request", json.dumps(payload), qos=1)
        if info.rc != 0:
            raise PrinterError(f"H2S MQTT publish failed (rc={info.rc})")

    def status(self) -> PrinterStatus:
        with self._lock:
            report = copy.deepcopy(self._report)
            age = time.monotonic() - self._last_msg
        if not report or age > 60:
            return PrinterStatus(printer=self.name, state=State.OFFLINE,
                                 error="no MQTT report in 60 s")
        return parse_report(report, self.door_field, self.name)

    def _upload(self, local: Path, remote_name: str) -> None:
        ftp = _ImplicitFTPS(context=_lan_tls_context(), timeout=30)
        try:
            ftp.connect(self.host, 990)
            ftp.login("bblp", self.code)
            ftp.prot_p()
            with local.open("rb") as fh:
                ftp.storbinary(f"STOR {remote_name}", fh)
        except (OSError, ftplib.Error) as exc:
            raise PrinterError(f"H2S upload failed: {type(exc).__name__}") from exc
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()

    def start(self, file_path: str, plate: int, ams_mapping: list[int] | None) -> None:
        local = Path(file_path)
        data = local.read_bytes()
        md5 = hashlib.md5(data).hexdigest()
        # Remote name is ours (hash-based), never the user's file name.
        remote = f"farm_{hashlib.sha256(data).hexdigest()[:12]}.3mf"
        self._upload(local, remote)
        url = self.file_url_template.format(name=remote)
        self._publish(cmd_project_file(self._next_seq(), remote, url, md5, plate, ams_mapping))

    def pause(self) -> None:
        self._publish(cmd_print(self._next_seq(), "pause"))

    def resume(self) -> None:
        self._publish(cmd_print(self._next_seq(), "resume"))

    def cancel(self) -> None:
        self._publish(cmd_print(self._next_seq(), "stop"))

    def set_light(self, on: bool) -> None:
        self._publish(cmd_light(self._next_seq(), on))

    def snapshot(self) -> bytes:
        url = f"rtsps://bblp:{self.code}@{self.host}:322/streaming/live/1"
        try:
            out = subprocess.run(
                ["ffmpeg", "-loglevel", "error", "-rtsp_transport", "tcp", "-i", url,
                 "-frames:v", "1", "-f", "image2", "-vcodec", "mjpeg", "-"],
                capture_output=True, timeout=20, check=True,
            )
        except FileNotFoundError as exc:
            raise PrinterError("ffmpeg not installed (see RUNBOOK_PHASE2.md)") from exc
        except (subprocess.SubprocessError, socket.timeout) as exc:
            raise PrinterError("H2S camera: no frame (is LAN Only Liveview on?)") from exc
        if not out.stdout:
            raise PrinterError("H2S camera returned an empty frame")
        return out.stdout
