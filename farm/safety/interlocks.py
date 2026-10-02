"""Preflight checks before a print starts. Every check returns pass/fail/warn + why."""
from __future__ import annotations

from dataclasses import dataclass

from ..printers.base import STARTABLE, PrinterStatus, Tray
from ..vision.bed_clear import BedCheck


@dataclass
class Check:
    name: str
    status: str  # "pass" | "fail" | "warn"
    detail: str


def map_filaments(required: list[dict], trays: list[Tray]) -> tuple[list[int] | None, str]:
    """Bambu ams_mapping: list index = filament id - 1, value = global tray slot.
    Match by material; prefer the same colour; skip empty trays."""
    if not required:
        return None, "file lists no filaments: printer will use its loaded filament"
    usable = [t for t in trays if t.remain_pct != 0]
    mapping: list[int] = [-1] * max(f["id"] for f in required)
    notes = []
    for f in sorted(required, key=lambda f: f["id"]):
        same = [t for t in usable if t.material == f["type"]]
        if not same:
            return None, f"needs {f['type']} (filament {f['id']}) but no AMS tray has it"
        exact = [t for t in same if t.color[:6] == f["color"][:6]]
        pick = (exact or same)[0]
        mapping[f["id"] - 1] = pick.slot
        notes.append(f"F{f['id']} {f['type']} #{f['color'][:6]} → tray {pick.slot}"
                     + ("" if exact else " (colour differs)"))
    return mapping, "; ".join(notes)


def start_checks(status: PrinterStatus, bed: BedCheck, required: list[dict] | None,
                 safety_layer_installed: bool) -> tuple[list[Check], list[int] | None]:
    checks = [
        Check("printer ready", "pass" if status.state in STARTABLE else "fail",
              f"state is {status.state.value}"),
        Check("bed clear (camera)", "pass" if bed.clear else "fail", bed.reason),
    ]
    if status.error:
        checks.append(Check("no printer error", "fail", status.error))

    ams_mapping = None
    if status.printer == "h2s":
        if status.door_open is None:
            checks.append(Check("door closed", "warn", "door state unknown: check the photo"))
        else:
            checks.append(Check("door closed", "fail" if status.door_open else "pass",
                                "door open" if status.door_open else "door closed"))
        ams_mapping, detail = map_filaments(required or [], status.trays)
        ok = ams_mapping is not None or not required
        checks.append(Check("filament loaded", "pass" if ok else "fail", detail))

    checks.append(Check(
        "safety layer", "pass" if safety_layer_installed else "warn",
        "smoke/heat cutoff active" if safety_layer_installed
        else "Phase 3 safety layer not installed: attended printing only",
    ))
    return checks, ams_mapping
