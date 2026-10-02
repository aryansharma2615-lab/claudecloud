"""Settings, read once from environment / .env. Secrets never live in code or git."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    dry_run: bool
    printers: tuple[str, ...]  # which printers are connected, e.g. ("ender",)
    data_dir: Path
    # Bambu H2S (LAN-only + Developer Mode)
    bambu_host: str
    bambu_serial: str
    bambu_access_code: str
    bambu_file_url_template: str
    bambu_door_field: str  # dotted path in the MQTT report; "" = unknown (Gate 1 Q2)
    # Ender via OctoPrint
    octoprint_url: str
    octoprint_api_key: str
    ender_camera_index: int
    # MCP server
    host: str
    port: int
    public_url: str
    github_client_id: str
    github_client_secret: str
    allowed_github_login: str
    jwt_signing_key: str
    # Alerts
    pushover_token: str
    pushover_user: str

    @property
    def db_path(self) -> Path:
        return self.data_dir / "farm.sqlite3"

    @property
    def library_dir(self) -> Path:
        return self.data_dir / "library"

    @property
    def vision_dir(self) -> Path:
        return self.data_dir / "vision"


def load_settings(env_file: str | None = None) -> Settings:
    load_dotenv(env_file)
    g = os.getenv
    return Settings(
        dry_run=_bool("FARM_DRY_RUN", True),  # safe default: no hardware touched
        printers=tuple(n.strip() for n in g("FARM_PRINTERS", "h2s,ender").split(",")
                       if n.strip() in ("h2s", "ender")),
        data_dir=Path(g("FARM_DATA_DIR", "data")).resolve(),
        bambu_host=g("BAMBU_HOST", ""),
        bambu_serial=g("BAMBU_SERIAL", ""),
        bambu_access_code=g("BAMBU_ACCESS_CODE", ""),
        bambu_file_url_template=g("BAMBU_FILE_URL_TEMPLATE", "file:///sdcard/{name}"),
        bambu_door_field=g("BAMBU_DOOR_FIELD", ""),
        octoprint_url=g("OCTOPRINT_URL", "http://127.0.0.1:5000").rstrip("/"),
        octoprint_api_key=g("OCTOPRINT_API_KEY", ""),
        ender_camera_index=int(g("ENDER_CAMERA_INDEX", "0")),
        host=g("FARM_HOST", "127.0.0.1"),
        port=int(g("FARM_PORT", "8765")),
        public_url=g("FARM_PUBLIC_URL", "http://127.0.0.1:8765"),
        github_client_id=g("GITHUB_CLIENT_ID", ""),
        github_client_secret=g("GITHUB_CLIENT_SECRET", ""),
        allowed_github_login=g("FARM_ALLOWED_GITHUB_LOGIN", "").strip().lower(),
        jwt_signing_key=g("FARM_JWT_SIGNING_KEY", ""),
        pushover_token=g("PUSHOVER_TOKEN", ""),
        pushover_user=g("PUSHOVER_USER", ""),
    )
