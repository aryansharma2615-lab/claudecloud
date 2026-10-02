"""Approved print library. Claude can only print files a human added here.

Files are copied in, identified by sha256 (file_id = first 12 hex chars), and
re-hashed before every print so a swapped file is refused.
H2S: .3mf sliced in Bambu Studio/OrcaSlicer (contains Metadata/plate_N.gcode).
Ender: .gcode.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .printers.base import clean_text
from .store import Store

EXT = {"h2s": ".3mf", "ender": ".gcode"}


class LibraryError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_3mf_plates(path: Path) -> dict[str, list[dict]]:
    """{plate_number: [{"id": filament id, "type": "PLA", "color": "FFFFFF"}...]}"""
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            gcode_plates = sorted(int(m.group(1)) for n in names
                                  if (m := re.fullmatch(r"Metadata/plate_(\d+)\.gcode", n)))
            if not gcode_plates:
                raise LibraryError("this .3mf has no sliced plates: slice and export "
                                   "'plate sliced file' first")
            info = z.read("Metadata/slice_info.config") if "Metadata/slice_info.config" in names else b""
    except zipfile.BadZipFile as exc:
        raise LibraryError("not a valid .3mf") from exc

    plates: dict[str, list[dict]] = {str(p): [] for p in gcode_plates}
    if info:
        root = ET.fromstring(info)
        for plate in root.iter("plate"):
            idx = next((m.get("value") for m in plate.iter("metadata") if m.get("key") == "index"), None)
            if idx not in plates:
                continue
            plates[idx] = [
                {"id": int(f.get("id", "1")),
                 "type": clean_text(f.get("type"), 16).upper(),
                 "color": clean_text(f.get("color"), 9).lstrip("#").upper()}
                for f in plate.iter("filament")
            ]
    return plates


def add_file(store: Store, library_dir: Path, printer: str, src: Path, name: str | None = None) -> dict:
    if printer not in EXT:
        raise LibraryError(f"unknown printer {printer!r}")
    if not src.name.lower().endswith(EXT[printer]):
        raise LibraryError(f"{printer} needs a {EXT[printer]} file")
    plates = read_3mf_plates(src) if printer == "h2s" else {"1": []}
    digest = sha256_file(src)
    file_id = digest[:12]
    dest_dir = library_dir / printer
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{file_id}{EXT[printer]}"
    shutil.copy2(src, dest)
    display = clean_text(name or src.stem, 60)
    store.add_file(file_id, printer, display, digest, str(dest), plates)
    return store.get_file(file_id)


def verified_path(entry: dict) -> Path:
    path = Path(entry["path"])
    if not path.exists() or sha256_file(path) != entry["sha256"]:
        raise LibraryError("library file missing or changed since it was approved")
    return path
