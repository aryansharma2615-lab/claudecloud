import pytest
from farm.robot_link import crc16, seal, unseal


def test_crc_check_value():
    assert crc16(b"123456789") == 0x29B1          # same check value as firmware host_test.cpp


def test_roundtrip_and_firmware_format():
    line = seal({"seq": 1, "cmd": "hello"})
    assert line.startswith('{"seq":1,"cmd":"hello","crc":"')
    assert unseal(line) == {"seq": 1, "cmd": "hello"}


def test_corruption_rejected():
    line = seal({"seq": 2, "cmd": "move", "j": [100, 100, 0, 0, 0], "zone": "h2s"})
    with pytest.raises(ValueError):
        unseal(line.replace("100", "900", 1))
