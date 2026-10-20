"""NTAG215 Memory Layout and Page Formatter.

Generates exact 135-page (540 bytes) binary maps conforming to NXP NTAG215
specifications and NFC Forum Type 2 Tag Operation.
"""

import os
from typing import List, Tuple, Optional

TOTAL_PAGES = 135
PAGE_SIZE = 4
TOTAL_SIZE = TOTAL_PAGES * PAGE_SIZE  # 540 bytes
USER_START_PAGE = 4
USER_END_PAGE = 129  # Inclusive, 126 pages * 4 = 504 bytes


def generate_valid_uid() -> Tuple[bytes, int, int]:
    """Generate a random 7-byte NTAG215 UID and corresponding BCC bytes.

    Returns:
        (uid_bytes, bcc0, bcc1)
    """
    # NXP UIDs always begin with manufacturer code 0x04
    uid = bytes([0x04]) + os.urandom(6)
    bcc0 = 0x88 ^ uid[0] ^ uid[1] ^ uid[2]
    bcc1 = uid[3] ^ uid[4] ^ uid[5] ^ uid[6]
    return uid, bcc0, bcc1


def format_ntag215_memory(tlv_data: bytes, uid_override: Optional[bytes] = None) -> List[bytes]:
    """Format a complete 135-page NTAG215 memory layout.

    Args:
        tlv_data: NDEF TLV byte payload (must fit within 504 user bytes).
        uid_override: Optional 7-byte UID.

    Returns:
        List of 135 4-byte pages.
    """
    max_user_bytes = (USER_END_PAGE - USER_START_PAGE + 1) * PAGE_SIZE
    if len(tlv_data) > max_user_bytes:
        raise ValueError(
            f"Payload size ({len(tlv_data)} bytes) exceeds NTAG215 user memory capacity ({max_user_bytes} bytes). "
            "Consider shortening the URL or vCard content."
        )

    if uid_override:
        if len(uid_override) != 7:
            raise ValueError("UID must be exactly 7 bytes long.")
        uid = uid_override
        bcc0 = 0x88 ^ uid[0] ^ uid[1] ^ uid[2]
        bcc1 = uid[3] ^ uid[4] ^ uid[5] ^ uid[6]
    else:
        uid, bcc0, bcc1 = generate_valid_uid()

    pages: List[bytearray] = [bytearray(PAGE_SIZE) for _ in range(TOTAL_PAGES)]

    # Page 0: UID0..2 + BCC0
    pages[0] = bytearray([uid[0], uid[1], uid[2], bcc0])

    # Page 1: UID3..6
    pages[1] = bytearray([uid[3], uid[4], uid[5], uid[6]])

    # Page 2: BCC1 + Internal byte (0x48) + Static Lock bytes (0x00, 0x00)
    pages[2] = bytearray([bcc1, 0x48, 0x00, 0x00])

    # Page 3: Capability Container (CC) for NTAG215
    # Byte 0: 0xE1 (NDEF Magic)
    # Byte 1: 0x10 (NFC Forum Version 1.0)
    # Byte 2: 0x6D (Size indicator: 0x6D = 109 -> 109 * 8 = 872 bytes / 504 bytes user memory)
    # Byte 3: 0x00 (Read/Write open access)
    pages[3] = bytearray([0xE1, 0x10, 0x6D, 0x00])

    # User pages: Page 4 through Page 129
    # Pad tlv_data to fill user pages
    padded_user_data = tlv_data + b"\x00" * (max_user_bytes - len(tlv_data))
    for i in range(USER_START_PAGE, USER_END_PAGE + 1):
        offset = (i - USER_START_PAGE) * PAGE_SIZE
        pages[i] = bytearray(padded_user_data[offset : offset + PAGE_SIZE])

    # Page 130: Dynamic Lock Bytes
    pages[130] = bytearray([0x00, 0x00, 0x00, 0xBD])

    # Page 131: Configuration Page 0 (Mirror / Auth / CFG)
    pages[131] = bytearray([0x04, 0x00, 0x00, 0xFF])

    # Page 132: Configuration Page 1 (Access / Mod)
    pages[132] = bytearray([0x00, 0x05, 0x00, 0x00])

    # Page 133: Password (default blank/disabled: FF FF FF FF)
    pages[133] = bytearray([0xFF, 0xFF, 0xFF, 0xFF])

    # Page 134: PACK (Password Acknowledge: 00 00 00 00)
    pages[134] = bytearray([0x00, 0x00, 0x00, 0x00])

    return [bytes(p) for p in pages]
