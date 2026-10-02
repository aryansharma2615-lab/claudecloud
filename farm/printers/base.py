"""One printer interface, two drivers (Bambu MQTT, OctoPrint REST) plus a dry-run fake."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Protocol


class State(str, Enum):
    OFFLINE = "offline"
    IDLE = "idle"
    PREPARING = "preparing"
    PRINTING = "printing"
    PAUSED = "paused"
    FINISHED = "finished"
    FAILED = "failed"
    ERROR = "error"


STARTABLE = {State.IDLE, State.FINISHED}
BUSY = {State.PREPARING, State.PRINTING, State.PAUSED}


@dataclass
class Tray:
    slot: int  # global index used by Bambu ams_mapping: ams_id * 4 + tray_id
    material: str
    color: str
    remain_pct: int | None


@dataclass
class PrinterStatus:
    printer: str
    state: State
    job_name: str = ""  # untrusted text from the printer: sanitised, never executed
    progress_pct: float | None = None
    remaining_min: int | None = None
    nozzle_c: float | None = None
    bed_c: float | None = None
    chamber_c: float | None = None
    door_open: bool | None = None  # None = unknown
    error: str = ""
    trays: list[Tray] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        return d


_CTRL = re.compile(r"[\x00-\x1f\x7f]")


def clean_text(value: object, limit: int = 80) -> str:
    """Untrusted printer/file text → short, printable, inert string."""
    return _CTRL.sub(" ", str(value or ""))[:limit].strip()


class Printer(Protocol):
    name: str

    def status(self) -> PrinterStatus: ...
    def start(self, file_path: str, plate: int, ams_mapping: list[int] | None) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def cancel(self) -> None: ...
    def set_light(self, on: bool) -> None: ...
    def snapshot(self) -> bytes: ...  # JPEG


class PrinterError(RuntimeError):
    """Driver could not do what was asked; message is safe to show the user."""
