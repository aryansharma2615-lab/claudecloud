import pytest

from farm.library import add_file
from farm.printers.base import State
from farm.service import FarmError
from tests.conftest import make_3mf, put_part_on_bed, save_reference


def _approve(farm, tmp_path, filaments=((1, "PLA", "FFFFFF"),)):
    f = make_3mf(tmp_path / "bracket.3mf", list(filaments))
    return add_file(farm.store, tmp_path / "lib", "h2s", f, "Bracket")["file_id"]


def test_happy_path_start_needs_explicit_confirm(farm, tmp_path):
    fid = _approve(farm, tmp_path)
    save_reference(farm, "h2s")
    pre, photo = farm.start_print("shawarma", "h2s", fid, 1)
    assert pre["ready"] and photo and pre["ams_mapping"] == [0]
    assert farm.printers["h2s"].state == State.IDLE  # preflight alone starts nothing
    done = farm.confirm_action("shawarma", pre["confirm_token"])
    assert done["done"] and farm.printers["h2s"].state == State.PRINTING
    assert farm.printers["h2s"].calls[-1][0] == "start"
    with pytest.raises(FarmError):  # token is single use
        farm.confirm_action("shawarma", pre["confirm_token"])


def test_refuses_without_empty_bed_reference(farm, tmp_path):
    fid = _approve(farm, tmp_path)
    pre, _ = farm.start_print("shawarma", "h2s", fid, 1)
    assert not pre["ready"] and "confirm_token" not in pre


def test_refuses_when_part_on_bed(farm, tmp_path):
    fid = _approve(farm, tmp_path)
    save_reference(farm, "h2s")
    put_part_on_bed(farm, "h2s")
    pre, _ = farm.start_print("shawarma", "h2s", fid, 1)
    bed = next(c for c in pre["checks"] if c["name"] == "bed clear (camera)")
    assert not pre["ready"] and bed["status"] == "fail"


def test_refuses_missing_filament(farm, tmp_path):
    fid = _approve(farm, tmp_path, filaments=((1, "TPU", "000000"),))
    save_reference(farm, "h2s")
    pre, _ = farm.start_print("shawarma", "h2s", fid, 1)
    assert not pre["ready"]


def test_unknown_file_or_wrong_printer_refused(farm, tmp_path):
    fid = _approve(farm, tmp_path)
    with pytest.raises(FarmError, match="approved library"):
        farm.start_print("shawarma", "h2s", "../../etc/passwd", 1)
    with pytest.raises(FarmError, match="approved library"):
        farm.start_print("shawarma", "ender", fid, 1)
    with pytest.raises(FarmError, match="plate"):
        farm.start_print("shawarma", "h2s", fid, 3)


def test_confirm_rechecks_state(farm, tmp_path):
    fid = _approve(farm, tmp_path)
    save_reference(farm, "h2s")
    pre, _ = farm.start_print("shawarma", "h2s", fid, 1)
    put_part_on_bed(farm, "h2s")  # someone drops a part between preflight and yes
    res = farm.confirm_action("shawarma", pre["confirm_token"])
    assert res["done"] is False and farm.printers["h2s"].state == State.IDLE


def test_stop_all_pauses_everything_without_confirm(farm):
    for p in farm.printers.values():
        p.state = State.PRINTING
    res = farm.stop_all("shawarma")
    assert res["printers"] == {"h2s": "paused", "ender": "paused"}
    assert all(p.state == State.PAUSED for p in farm.printers.values())


def test_resume_and_cancel_require_confirm(farm):
    farm.printers["ender"].state = State.PAUSED
    pre, _ = farm.request_resume("shawarma", "ender")
    assert farm.printers["ender"].state == State.PAUSED
    farm.confirm_action("shawarma", pre["confirm_token"])
    assert farm.printers["ender"].state == State.PRINTING
    pre, _ = farm.request_cancel("shawarma", "ender")
    farm.confirm_action("shawarma", pre["confirm_token"])
    assert farm.printers["ender"].state == State.IDLE
    with pytest.raises(FarmError, match="nothing to cancel"):
        farm.request_cancel("shawarma", "ender")


def test_every_call_is_logged(farm):
    farm.farm_status("shawarma")
    farm.stop_all("shawarma")
    tools = [row[2] for row in farm.store.recent_actions()]
    assert "farm_status" in tools and "stop_all" in tools


def test_watcher_alerts_on_finish(farm):
    farm.poll_once()
    farm.printers["h2s"].state = State.FINISHED
    farm.poll_once()
    assert any("finished" in t for t, _, _ in farm.notifier.sent)


def test_ender_light_is_a_clear_refusal(farm):
    with pytest.raises(FarmError, match="no software-controlled light"):
        farm.set_light("shawarma", "ender", True)
