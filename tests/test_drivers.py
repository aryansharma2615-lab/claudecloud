import json

import httpx
import pytest

from farm.printers import bambu
from farm.printers.base import State
from farm.printers.octoprint import OctoPrintPrinter, parse_status
from tests.conftest import fixture


def test_bambu_full_report_parses():
    st = bambu.parse_report(fixture("h2s_report_full.json"), door_field="print.stat.door")
    assert st.state == State.PRINTING
    assert st.progress_pct == 37 and st.remaining_min == 84
    assert st.bed_c == 55.0 and st.chamber_c == 31.0
    assert st.door_open is False
    assert [(t.slot, t.material, t.remain_pct) for t in st.trays] == [
        (0, "PLA", 80), (1, "PETG", 0), (2, "PETG", 60)]  # empty slot 3 skipped


def test_bambu_untrusted_name_is_sanitised():
    st = bambu.parse_report(fixture("h2s_report_full.json"))
    assert "\x07" not in st.job_name and len(st.job_name) <= 80
    assert st.door_open is None  # no door field configured → unknown, not "closed"


def test_bambu_delta_merges_onto_full_report():
    merged = bambu.deep_merge(fixture("h2s_report_full.json"), fixture("h2s_report_delta.json"))
    st = bambu.parse_report(merged)
    assert st.state == State.PAUSED and st.progress_pct == 38
    assert len(st.trays) == 3  # AMS data survives a delta without AMS


def test_bambu_error_when_idle_becomes_error_state():
    st = bambu.parse_report({"print": {"gcode_state": "IDLE", "print_error": 0x0300400C}})
    assert st.state == State.ERROR and "0x300400c" in st.error


def test_bambu_commands_shape():
    assert bambu.cmd_print(3, "pause") == {"print": {"sequence_id": "3", "command": "pause"}}
    with pytest.raises(ValueError):
        bambu.cmd_print(1, "gcode_line")
    pf = bambu.cmd_project_file(4, "farm_x.3mf", "file:///sdcard/farm_x.3mf", "abc", 2, [0, 2])
    assert pf["print"]["param"] == "Metadata/plate_2.gcode"
    assert pf["print"]["ams_mapping"] == [0, 2] and pf["print"]["use_ams"] is True
    with pytest.raises(ValueError):
        bambu.cmd_project_file(1, "a", "b", "c", 9, None)
    assert bambu.cmd_light(1, True)["system"]["led_mode"] == "on"


def test_octoprint_parse_printing():
    st = parse_status(fixture("octoprint_printer_printing.json"), fixture("octoprint_job_printing.json"))
    assert st.state == State.PRINTING and st.progress_pct == 12.3 and st.remaining_min == 65
    assert st.nozzle_c == 214.8 and st.bed_c == 60.1


def test_octoprint_parse_offline():
    assert parse_status(None, None).state == State.OFFLINE


def _octo(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://octo")
    return OctoPrintPrinter("http://octo", "", 0, client=client)


def test_octoprint_409_means_offline():
    p = _octo(lambda req: httpx.Response(409, text="Printer is not operational"))
    assert p.status().state == State.OFFLINE


def test_octoprint_pause_and_upload(tmp_path):
    seen = []

    def handler(req: httpx.Request):
        seen.append((req.method, req.url.path, req.content))
        return httpx.Response(204 if req.url.path == "/api/job" else 201, json={})

    p = _octo(handler)
    p.pause()
    assert seen[-1][:2] == ("POST", "/api/job")
    assert json.loads(seen[-1][2]) == {"command": "pause", "action": "pause"}
    g = tmp_path / "x.gcode"
    g.write_text("G28\n")
    p.start(str(g), 1, None)
    method, path, body = seen[-1]
    assert path == "/api/files/local" and b'name="print"' in body and b"farm_" in body


def test_octoprint_bad_key_reports_offline_with_reason():
    p = _octo(lambda req: httpx.Response(403))
    st = p.status()
    assert st.state == State.OFFLINE and "API key" in st.error
