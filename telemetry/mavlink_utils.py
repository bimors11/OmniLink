from __future__ import annotations

import struct


def x25_crc_init() -> int:
    return 0xFFFF


def x25_crc_accumulate(crc: int, b: int) -> int:
    tmp = (b ^ (crc & 0xFF)) & 0xFF
    tmp = (tmp ^ ((tmp << 4) & 0xFF)) & 0xFF
    crc = ((crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)) & 0xFFFF
    return crc


def x25_crc_accumulate_buf(crc: int, data: bytes) -> int:
    for bb in data:
        crc = x25_crc_accumulate(crc, bb)
    return crc


def mavlink_v1_heartbeat_packet(
    seq: int,
    sysid: int = 255,
    compid: int = 190,
    mav_type: int = 6,
    autopilot: int = 8,
    base_mode: int = 0,
    system_status: int = 0,
    custom_mode: int = 0,
) -> bytes:
    """
    Build MAVLink v1 HEARTBEAT packet (msgid=0).
    Includes x25 checksum with CRC extra 50.
    """
    stx = 0xFE
    payload_len = 9
    msgid = 0

    payload = struct.pack("<I", int(custom_mode) & 0xFFFFFFFF)
    payload += struct.pack(
        "<BBBBB",
        mav_type & 0xFF,
        autopilot & 0xFF,
        base_mode & 0xFF,
        system_status & 0xFF,
        3,  # mavlink_version
    )

    header = struct.pack("<BBBBB", payload_len, seq & 0xFF, sysid & 0xFF, compid & 0xFF, msgid & 0xFF)

    crc = x25_crc_init()
    crc = x25_crc_accumulate_buf(crc, header)
    crc = x25_crc_accumulate_buf(crc, payload)
    crc = x25_crc_accumulate(crc, 50)  # CRC extra for HEARTBEAT

    return bytes([stx]) + header + payload + struct.pack("<H", crc)
