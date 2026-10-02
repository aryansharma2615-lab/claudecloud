"""End-to-end through the real MCP layer (in-memory client, dry-run printers, no OAuth)."""
import json

import pytest
from fastmcp import Client

from farm.config import load_settings
from farm.mcp_server import build_server
from farm.service import FarmService
from farm.store import Store


@pytest.fixture
def server(farm):
    settings = load_settings(env_file="/nonexistent")
    return build_server(settings, farm)


async def test_tool_surface_has_no_raw_gcode(server):
    async with Client(server) as c:
        names = {t.name for t in await c.list_tools()}
    assert names == {"farm_status", "camera_snapshot", "list_library", "start_print",
                     "confirm_action", "resume", "cancel", "pause", "set_light", "stop_all"}
    assert not any("gcode" in n or "temp" in n or "jog" in n for n in names)


async def test_status_and_snapshot_over_mcp(server):
    async with Client(server) as c:
        res = await c.call_tool("farm_status", {})
        data = json.loads(res.content[0].text)
        assert {p["printer"] for p in data["printers"]} == {"h2s", "ender"}
        snap = await c.call_tool("camera_snapshot", {"camera": "h2s_live"})
        assert snap.content[0].type == "image"


async def test_bad_enum_rejected(server):
    async with Client(server) as c:
        with pytest.raises(Exception):
            await c.call_tool("pause", {"printer": "kitchen_oven"})


async def test_refusal_is_a_tool_error(server):
    async with Client(server) as c:
        with pytest.raises(Exception, match="approved library"):
            await c.call_tool("start_print", {"printer": "h2s", "file_id": "nope"})


def test_oauth_requires_allowlist(farm, monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret")
    monkeypatch.setenv("FARM_ALLOWED_GITHUB_LOGIN", "")
    with pytest.raises(SystemExit, match="ALLOWED"):
        build_server(load_settings(env_file="/nonexistent"), farm)
    monkeypatch.setenv("FARM_ALLOWED_GITHUB_LOGIN", "Shawarma")
    s = load_settings(env_file="/nonexistent")
    assert s.allowed_github_login == "shawarma"
    build_server(s, farm)  # GitHubProvider constructs


def test_no_oauth_refuses_public_bind(farm, monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.setenv("FARM_HOST", "0.0.0.0")
    with pytest.raises(SystemExit, match="127.0.0.1"):
        build_server(load_settings(env_file="/nonexistent"), farm)


async def _call_local_only(headers, client=("127.0.0.1", 5000)):
    from farm.mcp_server import LocalOnly
    seen = {}

    async def app(scope, receive, send):
        seen["passed"] = True

    async def send(msg):
        if msg["type"] == "http.response.start":
            seen["status"] = msg["status"]

    scope = {"type": "http", "headers": headers, "client": client}
    await LocalOnly(app)(scope, None, send)
    return seen


async def test_local_only_blocks_tunnelled_requests():
    assert (await _call_local_only([(b"host", b"127.0.0.1:8765")])).get("passed")
    assert (await _call_local_only([(b"host", b"farmpc.tail1.ts.net")]))["status"] == 403
    assert (await _call_local_only([(b"host", b"127.0.0.1:8765"),
                                    (b"x-forwarded-for", b"160.79.104.9")]))["status"] == 403
    assert (await _call_local_only([(b"host", b"localhost"), (b"tailscale-funnel-request", b"?1")]))["status"] == 403
    assert (await _call_local_only([(b"host", b"localhost")], client=("10.0.0.7", 1)))["status"] == 403


def test_ender_only_farm(monkeypatch, tmp_path):
    from farm.mcp_server import build_service
    from farm.service import FarmError
    monkeypatch.setenv("FARM_PRINTERS", "ender")
    monkeypatch.setenv("FARM_DRY_RUN", "1")
    monkeypatch.setenv("FARM_DATA_DIR", str(tmp_path))
    svc = build_service(load_settings(env_file="/nonexistent"))
    assert list(svc.printers) == ["ender"]
    assert [p["printer"] for p in svc.farm_status("u")["printers"]] == ["ender"]
    with pytest.raises(FarmError, match="not connected"):
        svc.set_light("u", "h2s", True)
    assert svc.stop_all("u")["printers"] == {"ender": "not printing"}
