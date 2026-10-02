"""OneShot Arm v5 — MCP server so Claude (Claude Code / Desktop / Cowork on the Mac) can see and move the arm.

  pip install fastmcp
  claude mcp add oneshot -- python /path/to/oneshot_v5/mac/oneshot_mcp.py      (Claude Code)
  or in Claude Desktop config: {"mcpServers": {"oneshot": {"command": "python", "args": ["/path/.../oneshot_mcp.py"],
                                 "env": {"ONESHOT_HOST": "oneshot.local", "ONESHOT_KEY": "change-me"}}}}
Runs locally over stdio: nothing is exposed to the internet.
"""
from fastmcp import FastMCP
from fastmcp.utilities.types import Image

import oneshot as arm

mcp = FastMCP("oneshot-arm")


@mcp.tool
def look(flash: bool = False) -> Image:
    """Take a photo with the ESP32-CAM above the arm and return it (use it to find the cube / check a grip)."""
    return Image(path=arm.look("/tmp/oneshot_look.jpg", flash))


@mcp.tool
def move(yaw: float, shoulder: float, elbow: float, ms: int = 1200) -> str:
    """Move the arm (degrees). Limits: yaw ±150, shoulder -40..45, elbow -45..45. Smooth min-jerk move."""
    return arm.move(yaw, shoulder, elbow, ms)


@mcp.tool
def grip(percent: float) -> str:
    """Gripper: 0 = open, 100 = fully closed. Close to ~70 for a 20 mm cube, check with look()."""
    return arm.grip(percent)


@mcp.tool
def home() -> str:
    """All joints to 0, gripper open."""
    return arm.home()


@mcp.tool
def stop() -> str:
    """Stop motion now. (The hardware E-stop button is the real safety stop.)"""
    return arm.stop()


@mcp.tool
def status() -> str:
    """Joint angles, E-stop / door state, Wi-Fi signal."""
    return arm.status()


if __name__ == "__main__":
    mcp.run()
