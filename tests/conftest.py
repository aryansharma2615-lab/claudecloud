import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from farm.notify.pushover import Notifier
from farm.printers.fake import FakePrinter
from farm.service import FarmService
from farm.store import Store
from farm.vision.cameras import encode_jpeg

FIX = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIX / name).read_text())


def make_3mf(path: Path, filaments: list[tuple[int, str, str]], plates=(1,)) -> Path:
    fil = "".join(f'<filament id="{i}" type="{t}" color="#{c}" used_g="5"/>' for i, t, c in filaments)
    info = "<config>" + "".join(
        f'<plate><metadata key="index" value="{p}"/>{fil}</plate>' for p in plates) + "</config>"
    with zipfile.ZipFile(path, "w") as z:
        for p in plates:
            z.writestr(f"Metadata/plate_{p}.gcode", "; fake\nG28\n")
        z.writestr("Metadata/slice_info.config", info)
    return path


class RecordingNotifier(Notifier):
    def __init__(self):
        super().__init__("", "")
        self.sent = []

    def send(self, title, message, priority=0, image_jpeg=None):
        self.sent.append((title, message, priority))
        return True


@pytest.fixture
def farm(tmp_path):
    printers = {"h2s": FakePrinter("h2s"), "ender": FakePrinter("ender")}
    vision = tmp_path / "vision"
    vision.mkdir()
    svc = FarmService(printers, Store(tmp_path / "farm.sqlite3"), vision, RecordingNotifier())
    return svc


def save_reference(svc: FarmService, printer: str) -> None:
    img = svc.printers[printer].bed_image
    (svc.vision_dir / f"{printer}_empty.jpg").write_bytes(encode_jpeg(img))


def put_part_on_bed(svc: FarmService, printer: str) -> None:
    img = svc.printers[printer].bed_image.copy()
    img[150:330, 200:440] = 230  # a bright part in the middle of the bed
    svc.printers[printer].bed_image = img
