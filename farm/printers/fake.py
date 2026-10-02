"""Dry-run printers: same interface, no hardware. FARM_DRY_RUN=1 (the default)."""
from __future__ import annotations

import numpy as np

from ..vision.cameras import encode_jpeg
from .base import PrinterError, PrinterStatus, State, Tray


class FakePrinter:
    def __init__(self, name: str, trays: list[Tray] | None = None):
        self.name = name
        self.state = State.IDLE
        self.job = ""
        self.light = False
        self.bed_c = 24.0
        self.trays = trays if trays is not None else (
            [Tray(0, "PLA", "FFFFFFFF", 80), Tray(1, "PETG", "000000FF", 50)] if name == "h2s" else []
        )
        self.calls: list[tuple] = []
        self.bed_image = np.full((480, 640, 3), 90, np.uint8)  # "empty bed"

    def status(self) -> PrinterStatus:
        return PrinterStatus(
            printer=self.name, state=self.state, job_name=self.job,
            progress_pct=0.0 if self.state == State.PRINTING else None,
            remaining_min=42 if self.state == State.PRINTING else None,
            nozzle_c=25.0, bed_c=self.bed_c, door_open=False if self.name == "h2s" else None,
            trays=list(self.trays),
        )

    def start(self, file_path: str, plate: int, ams_mapping: list[int] | None) -> None:
        if self.state not in (State.IDLE, State.FINISHED):
            raise PrinterError("fake printer busy")
        self.calls.append(("start", file_path, plate, ams_mapping))
        self.state, self.job = State.PRINTING, "dry-run job"

    def pause(self) -> None:
        self.calls.append(("pause",))
        if self.state == State.PRINTING:
            self.state = State.PAUSED

    def resume(self) -> None:
        self.calls.append(("resume",))
        if self.state == State.PAUSED:
            self.state = State.PRINTING

    def cancel(self) -> None:
        self.calls.append(("cancel",))
        self.state, self.job = State.IDLE, ""

    def set_light(self, on: bool) -> None:
        if self.name == "ender":
            raise PrinterError("The Ender has no software-controlled light")
        self.calls.append(("light", on))
        self.light = on

    def snapshot(self) -> bytes:
        return encode_jpeg(self.bed_image)
