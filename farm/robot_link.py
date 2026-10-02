"""PC side of the robot link (framing only). Must match firmware/farmhand_mc/include/protocol.h.

Line = JSON object with crc as the LAST key; crc = CRC-16/CCITT-FALSE of the line without ,"crc":"XXXX".
The planner/serial loop that uses this lives with Prompt B; this module pins the wire format.
"""
import json

CRC_KEY = ',"crc":"'


def crc16(data: bytes) -> int:
    c = 0xFFFF
    for b in data:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) if c & 0x8000 else (c << 1)
            c &= 0xFFFF
    return c


def seal(obj: dict) -> str:
    """dict -> one line (no newline). Key order is kept; crc is appended last."""
    body = json.dumps(obj, separators=(",", ":"))
    return body[:-1] + f'{CRC_KEY}{crc16(body.encode()):04X}"}}'


def unseal(line: str) -> dict:
    line = line.strip()
    p = line.rfind(CRC_KEY)
    if p < 0 or not line.endswith('"}') or len(line) != p + len(CRC_KEY) + 6:
        raise ValueError("no crc")
    body = line[:p] + "}"
    if crc16(body.encode()) != int(line[p + len(CRC_KEY):p + len(CRC_KEY) + 4], 16):
        raise ValueError("crc mismatch")
    return json.loads(body)
