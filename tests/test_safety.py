import time

import numpy as np
import pytest

from farm.library import LibraryError, add_file, read_3mf_plates, verified_path
from farm.printers.base import Tray
from farm.safety.confirm import ConfirmTokens
from farm.safety.interlocks import map_filaments
from farm.safety.ratelimit import RateLimiter
from farm.store import Store
from farm.vision import bed_clear
from tests.conftest import make_3mf


def test_3mf_plates_and_filaments(tmp_path):
    f = make_3mf(tmp_path / "b.3mf", [(1, "PLA", "FFFFFF"), (2, "PETG", "FF0000")], plates=(1, 2))
    plates = read_3mf_plates(f)
    assert set(plates) == {"1", "2"}
    assert plates["1"][1] == {"id": 2, "type": "PETG", "color": "FF0000"}


def test_unsliced_3mf_rejected(tmp_path):
    import zipfile
    p = tmp_path / "raw.3mf"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("3D/3dmodel.model", "<model/>")
    with pytest.raises(LibraryError, match="no sliced plates"):
        read_3mf_plates(p)


def test_library_wrong_extension_and_tamper(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    g = tmp_path / "part.gcode"
    g.write_text("G28\n")
    with pytest.raises(LibraryError):
        add_file(store, tmp_path / "lib", "h2s", g)
    entry = add_file(store, tmp_path / "lib", "ender", g, "Part")
    assert verified_path(entry).exists()
    with open(entry["path"], "a") as fh:
        fh.write("M104 S300\n")  # someone edits the approved file
    with pytest.raises(LibraryError, match="changed"):
        verified_path(entry)


def test_filament_mapping_prefers_colour_and_skips_empty():
    trays = [Tray(0, "PLA", "FFFFFFFF", 80), Tray(1, "PETG", "000000FF", 0), Tray(2, "PETG", "FF0000FF", 60)]
    mapping, note = map_filaments([{"id": 1, "type": "PLA", "color": "FFFFFF"},
                                   {"id": 2, "type": "PETG", "color": "000000"}], trays)
    assert mapping == [0, 2]  # black PETG tray is empty → red PETG, flagged
    assert "colour differs" in note
    assert map_filaments([{"id": 1, "type": "TPU", "color": "000000"}], trays)[0] is None


def test_confirm_token_single_use_user_bound_and_expires():
    t = ConfirmTokens(ttl_s=0.2)
    tok = t.issue("cancel", {"printer": "h2s"}, "shawarma")
    with pytest.raises(PermissionError):
        t.consume(tok, "mallory")
    tok = t.issue("cancel", {"printer": "h2s"}, "shawarma")
    assert t.consume(tok, "shawarma").action == "cancel"
    with pytest.raises(PermissionError):
        t.consume(tok, "shawarma")
    tok = t.issue("cancel", {}, "shawarma")
    time.sleep(0.25)
    with pytest.raises(PermissionError, match="expired"):
        t.consume(tok, "shawarma")


def test_rate_limit_and_exemptions():
    rl = RateLimiter({"any": (100, 60), "action": (2, 60)})
    rl.check("u", "start_print", True)
    rl.check("u", "cancel", True)
    with pytest.raises(PermissionError):
        rl.check("u", "resume", True)
    for _ in range(10):
        rl.check("u", "stop_all", True)  # never limited


def test_bed_clear_compare_and_fail_closed(tmp_path):
    ref = np.full((240, 320, 3), 90, np.uint8)
    assert bed_clear.compare(ref.copy(), ref).clear
    part = ref.copy()
    part[60:180, 100:220] = 230
    assert not bed_clear.compare(part, ref).clear
    assert not bed_clear.compare(part, ref.copy()[:200]).clear  # resolution changed
    # ROI that excludes the part → clear
    assert bed_clear.compare(part, ref, roi=(0, 0, 90, 240)).clear
    from farm.vision.cameras import encode_jpeg
    assert not bed_clear.check("h2s", encode_jpeg(ref), tmp_path).clear  # no reference
