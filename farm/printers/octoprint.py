"""Ender 3 S1 Pro via OctoPrint REST (https://docs.octoprint.org/en/master/api/).

The API key belongs to an OctoPrint user with PRINT permission but not CONTROL, so
even a leaked key can't jog axes or send raw G-code.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import httpx

from ..vision.cameras import UsbCamera
from .base import PrinterError, PrinterStatus, State, clean_text


def parse_status(printer_json: dict | None, job_json: dict | None) -> PrinterStatus:
    if printer_json is None:
        return PrinterStatus(printer="ender", state=State.OFFLINE,
                             error="OctoPrint not connected to the printer")
    flags = (printer_json.get("state") or {}).get("flags") or {}
    text = clean_text((printer_json.get("state") or {}).get("text"))
    if flags.get("error") or flags.get("closedOrError"):
        state = State.ERROR
    elif flags.get("paused") or flags.get("pausing"):
        state = State.PAUSED
    elif flags.get("printing") or flags.get("cancelling"):
        state = State.PRINTING
    elif flags.get("ready") or flags.get("operational"):
        state = State.IDLE
    else:
        state = State.OFFLINE

    temps = printer_json.get("temperature") or {}
    def actual(key: str) -> float | None:
        v = (temps.get(key) or {}).get("actual")
        return float(v) if isinstance(v, (int, float)) else None

    job = job_json or {}
    progress = (job.get("progress") or {})
    left = progress.get("printTimeLeft")
    completion = progress.get("completion")
    name = ((job.get("job") or {}).get("file") or {}).get("name")
    return PrinterStatus(
        printer="ender",
        state=state,
        job_name=clean_text(name) if state in (State.PRINTING, State.PAUSED) else "",
        progress_pct=round(float(completion), 1) if isinstance(completion, (int, float)) else None,
        remaining_min=int(left // 60) if isinstance(left, (int, float)) else None,
        nozzle_c=actual("tool0"),
        bed_c=actual("bed"),
        error=text if state == State.ERROR else "",
    )


class OctoPrintPrinter:
    name = "ender"

    def __init__(self, base_url: str, api_key: str, camera_index: int,
                 client: httpx.Client | None = None):
        if not api_key and client is None:
            raise PrinterError("Ender not configured: set OCTOPRINT_API_KEY")
        self._http = client or httpx.Client(base_url=base_url, timeout=15,
                                            headers={"X-Api-Key": api_key})
        self._camera = UsbCamera(camera_index)

    def _get(self, path: str) -> dict | None:
        try:
            r = self._http.get(path)
        except httpx.HTTPError as exc:
            raise PrinterError("OctoPrint unreachable") from exc
        if r.status_code == 409:  # printer not operational
            return None
        if r.status_code in (401, 403):
            raise PrinterError("OctoPrint rejected the API key")
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, body: dict) -> None:
        try:
            r = self._http.post(path, json=body)
        except httpx.HTTPError as exc:
            raise PrinterError("OctoPrint unreachable") from exc
        if r.status_code == 409:
            raise PrinterError("OctoPrint refused: printer not in a state for that")
        if r.status_code >= 400:
            raise PrinterError(f"OctoPrint error {r.status_code}")

    def status(self) -> PrinterStatus:
        try:
            p = self._get("/api/printer")
            j = self._get("/api/job") if p is not None else None
        except PrinterError as exc:
            return PrinterStatus(printer=self.name, state=State.OFFLINE, error=str(exc))
        return parse_status(p, j)

    def start(self, file_path: str, plate: int, ams_mapping: list[int] | None) -> None:
        data = Path(file_path).read_bytes()
        remote = f"farm_{hashlib.sha256(data).hexdigest()[:12]}.gcode"
        try:
            r = self._http.post(
                "/api/files/local",
                files={"file": (remote, data, "application/octet-stream")},
                data={"select": "true", "print": "true"},
                timeout=120,
            )
        except httpx.HTTPError as exc:
            raise PrinterError("OctoPrint upload failed") from exc
        if r.status_code >= 400:
            raise PrinterError(f"OctoPrint upload/print error {r.status_code}")

    def pause(self) -> None:
        self._post("/api/job", {"command": "pause", "action": "pause"})

    def resume(self) -> None:
        self._post("/api/job", {"command": "pause", "action": "resume"})

    def cancel(self) -> None:
        self._post("/api/job", {"command": "cancel"})

    def set_light(self, on: bool) -> None:
        raise PrinterError("The Ender has no software-controlled light")

    def snapshot(self) -> bytes:
        return self._camera.snapshot()
