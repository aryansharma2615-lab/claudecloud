from farm.ender_check import parse_m115

# Shape of a Marlin 2.x M115 reply (Creality S1 Pro stock firmware is Marlin-based).
REPLY = """FIRMWARE_NAME:Marlin 2.0.8.21 (Aug  9 2022 17:32:01) SOURCE_CODE_URL:www.creality.com PROTOCOL_VERSION:1.0 MACHINE_TYPE:Ender-3 S1 Pro EXTRUDER_COUNT:1 UUID:cede2a2f-41a2-4748-9b12-c55c62f367ff
Cap:SERIAL_XON_XOFF:0
Cap:AUTOREPORT_TEMP:1
Cap:THERMAL_PROTECTION:1
Cap:EMERGENCY_PARSER:1
ok
"""


def test_parse_m115():
    info = parse_m115(REPLY)
    assert info["firmware"].startswith("Marlin 2.0.8")
    assert info["machine"] == "Ender-3 S1 Pro"
    assert info["caps"]["THERMAL_PROTECTION"] is True
    assert info["caps"]["SERIAL_XON_XOFF"] is False


def test_parse_m115_garbage():
    assert parse_m115("\x00\xffecho:busy") == {"caps": {}}
