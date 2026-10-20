"""Flipper Zero .nfc File Serializer and Inspector.

Generates and parses official Flipper Zero NFC device files (Version 4, NTAG/Ultralight).
Strictly uses Unix LF (\n) line endings required by Flipper OS LittlevGL parser.
"""

from typing import List, Dict, Any
from flipper_bizcard.encoder.ndef import URI_PREFIXES


def serialize_flipper_nfc(pages: List[bytes], uid: bytes) -> str:
    """Serialize NTAG215 pages and UID into the official Flipper .nfc file format.

    Uses Device type: NTAG/Ultralight with Data format version: 2 and NTAG/Ultralight type: NTAG215.
    Ensures LF line endings.
    """
    uid_str = " ".join(f"{b:02X}" for b in uid)
    lines = [
        "Filetype: Flipper NFC device",
        "Version: 4",
        "# Device type can be ISO14443-3A, ISO14443-3B, ISO14443-4A, ISO14443-4B, ISO15693-3, FeliCa, NTAG/Ultralight, Mifare Classic, Mifare Plus, Mifare DESFire, SLIX, ST25TB",
        "Device type: NTAG/Ultralight",
        "# UID is common for all formats",
        f"UID: {uid_str}",
        "# ISO14443-3A specific data",
        "ATQA: 00 44",
        "SAK: 00",
        "# NTAG/Ultralight specific data",
        "Data format version: 2",
        "NTAG/Ultralight type: NTAG215",
        "Signature: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00",
        "Mifare version: 00 04 04 02 01 00 11 03",
        "Counter 0: 0",
        "Tearing 0: 00",
        "Counter 1: 0",
        "Tearing 1: 00",
        "Counter 2: 0",
        "Tearing 2: 00",
        f"Pages total: {len(pages)}",
        f"Pages read: {len(pages)}",
    ]

    for idx, page in enumerate(pages):
        page_hex = " ".join(f"{b:02X}" for b in page)
        lines.append(f"Page {idx}: {page_hex}")

    lines.append("Failed authentication attempts: 0")
    # Join with strict Unix LF line endings
    return "\n".join(lines) + "\n"


def parse_flipper_nfc(content: str) -> Dict[str, Any]:
    """Parse a Flipper .nfc file and extract metadata and decoded NDEF records."""
    metadata: Dict[str, Any] = {
        "filetype": None,
        "version": None,
        "device_type": None,
        "ntag_type": None,
        "uid": None,
        "atqa": None,
        "sak": None,
        "pages": {},
        "raw_user_bytes": bytearray(),
        "ndef_records": [],
        "ios_compatible": False,
        "compatibility_notes": [],
    }

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip()

            if key == "Filetype":
                metadata["filetype"] = val
            elif key == "Version":
                metadata["version"] = val
            elif key == "Device type":
                metadata["device_type"] = val
            elif key == "NTAG/Ultralight type":
                metadata["ntag_type"] = val
            elif key == "UID":
                metadata["uid"] = val
            elif key == "ATQA":
                metadata["atqa"] = val
            elif key == "SAK":
                metadata["sak"] = val
            elif key.startswith("Page "):
                try:
                    page_idx = int(key.split()[1])
                    bytes_val = bytes.fromhex(val.replace(" ", ""))
                    metadata["pages"][page_idx] = bytes_val
                except Exception:
                    pass

    # Check compatibility
    is_ntag = metadata.get("device_type") == "NTAG/Ultralight" or metadata.get("ntag_type") in ("NTAG215", "NTAG213", "NTAG216")
    if is_ntag:
        metadata["compatibility_notes"].append("Device type is supported by iOS background NFC.")
    else:
        metadata["compatibility_notes"].append(
            f"Warning: Device type '{metadata.get('device_type')}' may not be supported by iOS background reader."
        )

    # Reconstruct user memory (Pages 4 to 129)
    user_bytes = bytearray()
    for p in range(4, 130):
        if p in metadata["pages"]:
            user_bytes.extend(metadata["pages"][p])
    metadata["raw_user_bytes"] = bytes(user_bytes)

    # Check Capability Container (Page 3)
    p3 = metadata["pages"].get(3)
    if p3 and len(p3) >= 4 and p3[0] == 0xE1:
        metadata["compatibility_notes"].append(
            f"Valid CC Container detected (0xE1, Version {(p3[1] >> 4)}.{p3[1] & 0x0F})."
        )
    else:
        metadata["compatibility_notes"].append(
            "Warning: Page 3 does not contain valid NFC Forum CC magic (0xE1)."
        )

    # Decode NDEF from user memory
    _decode_ndef_tlv(metadata["raw_user_bytes"], metadata)

    if metadata["ndef_records"] and is_ntag:
        metadata["ios_compatible"] = True

    return metadata


def _decode_ndef_tlv(user_bytes: bytes, metadata: Dict[str, Any]):
    """Decode TLV structures and extract NDEF payloads."""
    idx = 0
    total = len(user_bytes)

    while idx < total:
        tlv_type = user_bytes[idx]
        idx += 1

        if tlv_type == 0x00:  # NULL TLV
            continue
        elif tlv_type == 0xFE:  # Terminator TLV
            break
        elif tlv_type == 0x03:  # NDEF Message
            if idx >= total:
                break
            length = user_bytes[idx]
            idx += 1
            if length == 0xFF:  # 3-byte format
                if idx + 2 > total:
                    break
                length = int.from_bytes(user_bytes[idx : idx + 2], byteorder="big")
                idx += 2

            ndef_message = user_bytes[idx : idx + length]
            idx += length
            _parse_ndef_records(ndef_message, metadata)
        else:
            # Skip unknown TLV
            if idx >= total:
                break
            length = user_bytes[idx]
            idx += 1 + length


def _parse_ndef_records(message: bytes, metadata: Dict[str, Any]):
    """Parse NDEF record headers and payload."""
    idx = 0
    total = len(message)

    while idx < total:
        header = message[idx]
        idx += 1

        mb = bool(header & 0x80)
        me = bool(header & 0x40)
        cf = bool(header & 0x20)
        sr = bool(header & 0x10)
        il = bool(header & 0x08)
        tnf = header & 0x07

        if idx >= total:
            break
        type_len = message[idx]
        idx += 1

        if sr:
            if idx >= total:
                break
            payload_len = message[idx]
            idx += 1
        else:
            if idx + 4 > total:
                break
            payload_len = int.from_bytes(message[idx : idx + 4], byteorder="big")
            idx += 4

        id_len = 0
        if il:
            if idx >= total:
                break
            id_len = message[idx]
            idx += 1

        rec_type = message[idx : idx + type_len]
        idx += type_len

        rec_id = message[idx : idx + id_len]
        idx += id_len

        payload = message[idx : idx + payload_len]
        idx += payload_len

        record_info = {
            "tnf": tnf,
            "type": rec_type.decode("latin1", errors="replace"),
            "payload_len": payload_len,
            "decoded_content": None,
        }

        # Decode Well-Known Type 'U' (URI)
        if tnf == 0x01 and rec_type == b"U" and len(payload) > 0:
            prefix_code = payload[0]
            prefix_str = URI_PREFIXES.get(prefix_code, "")
            uri_suffix = payload[1:].decode("utf-8", errors="replace")
            record_info["decoded_content"] = f"{prefix_str}{uri_suffix}"
            record_info["kind"] = "URI / Website"

        # Decode MIME type vCard
        elif tnf == 0x02 and rec_type.lower() == b"text/vcard":
            vcard_text = payload.decode("utf-8", errors="replace")
            record_info["decoded_content"] = vcard_text
            record_info["kind"] = "vCard Contact Card"

        metadata["ndef_records"].append(record_info)

        if me:
            break