"""OneShot Arm v5 — Mac-side client for the ESP32-CAM bridge. Library + CLI.

  export ONESHOT_HOST=oneshot.local ONESHOT_KEY=change-me
  python oneshot.py look shot.jpg          # save a photo (Claude reads the file to see the table)
  python oneshot.py move 30 10 -5 [ms]     # yaw, shoulder, elbow (arm degrees)
  python oneshot.py grip 80                # 0 open .. 100 closed
  python oneshot.py home | stop | status | zero
  python oneshot.py raw "J 0 0 0 1500"     # any UNO line
"""
import os
import sys
import time
import urllib.parse
import urllib.request

HOST = os.environ.get("ONESHOT_HOST", "oneshot.local")
KEY = os.environ.get("ONESHOT_KEY", "change-me")
LIMITS = {"yaw": 150, "sh": (-40, 45), "el": (-45, 45)}     # must match uno_arm.ino


def _get(path, params=None, timeout=25):
    q = {"k": KEY, **(params or {})}
    url = f"http://{HOST}{path}?{urllib.parse.urlencode(q)}"
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def cmd(line, wait_ms=3000):
    out = _get("/cmd", {"c": line, "t": str(wait_ms)}, timeout=wait_ms / 1000 + 5).decode()
    if "ERR" in out:
        raise RuntimeError(f"UNO refused '{line}': {out.strip()}")
    return out


def status():
    return _get("/status").decode()


def look(path="oneshot.jpg", flash=False):
    data = _get("/capture", {"flash": "1" if flash else "0"})
    with open(path, "wb") as f:
        f.write(data)
    return path


def wait_done(timeout_s=20):
    t = time.time()
    while time.time() - t < timeout_s:            # polling also feeds the bridge's 3 s dead-man watchdog
        if "idle" in status():
            return True
        time.sleep(0.4)
    cmd("X")
    raise TimeoutError("move did not finish; sent stop")


def move(yaw, sh, el, ms=1200):
    if abs(yaw) > LIMITS["yaw"] or not (LIMITS["sh"][0] <= sh <= LIMITS["sh"][1]) or not (LIMITS["el"][0] <= el <= LIMITS["el"][1]):
        raise ValueError("outside joint limits")
    out = cmd(f"J {yaw:.1f} {sh:.1f} {el:.1f} {int(ms)}", wait_ms=int(ms) + 1500)
    if "DONE" not in out:
        wait_done()
    return "done"


def grip(pct, ms=600):
    out = cmd(f"G {pct:.0f} {int(ms)}", wait_ms=int(ms) + 1500)
    if "DONE" not in out:
        wait_done()
    return "done"


def home():
    out = cmd("H", wait_ms=6000)
    if "DONE" not in out:
        wait_done()
    return "done"


def stop():
    return cmd("X", wait_ms=500)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(0)
    op = a[0]
    if op == "look": print(look(a[1] if len(a) > 1 else "oneshot.jpg", flash="--flash" in a))
    elif op == "move": print(move(*map(float, a[1:4]), *(int(a[4]),) if len(a) > 4 else ()))
    elif op == "grip": print(grip(float(a[1])))
    elif op == "home": print(home())
    elif op == "stop": print(stop())
    elif op == "zero": print(cmd("Z"))
    elif op == "status": print(status())
    elif op == "raw": print(cmd(" ".join(a[1:]), 5000))
    else: print(__doc__)
