"""NDEF (NFC Data Exchange Format) Message and Record Builders.

Complies with NFC Forum Data Exchange Format (NDEF) Technical Specification.
"""

from typing import Optional, Dict

# Standard URI Identifier Codes (NFC Forum RTD URI 1.0)
URI_PREFIXES: Dict[int, str] = {
    0x01: "http://www.",
    0x02: "https://www.",
    0x03: "http://",
    0x04: "https://",
    0x05: "tel:",
    0x06: "mailto:",
    0x07: "ftp://anonymous:anonymous@",
    0x08: "ftp://ftp.",
    0x09: "ftps://",
    0x0A: "sftp://",
    0x0B: "smb://",
    0x0C: "nfs://",
    0x0D: "ftp://",
    0x0E: "dav://",
    0x0F: "news:",
    0x10: "telnet://",
    0x11: "imap:",
    0x12: "rtsp://",
    0x13: "urn:",
    0x14: "pop:",
    0x15: "sip:",
    0x16: "sips:",
    0x17: "tftp:",
    0x18: "btspp://",
    0x19: "btl2cap://",
    0x1A: "btgoep://",
    0x1B: "tcpobex://",
    0x1C: "irdaobex://",
    0x1D: "file://",
    0x1E: "urn:epc:id:",
    0x1F: "urn:epc:tag:",
    0x20: "urn:epc:pat:",
    0x21: "urn:epc:raw:",
    0x22: "urn:epc:",
    0x23: "urn:nfc:",
}


def build_uri_record(url: str, is_first: bool = True, is_last: bool = True) -> bytes:
    """Build an NDEF Well-Known Type 'U' (URI) record."""
    prefix_code = 0x00
    suffix = url

    # Find longest matching prefix
    for code, prefix in sorted(URI_PREFIXES.items(), key=lambda x: len(x[1]), reverse=True):
        if url.startswith(prefix):
            prefix_code = code
            suffix = url[len(prefix):]
            break

    payload = bytes([prefix_code]) + suffix.encode("utf-8")
    type_bytes = b"U"

    mb = 1 if is_first else 0
    me = 1 if is_last else 0
    cf = 0
    sr = 1 if len(payload) <= 255 else 0
    il = 0
    tnf = 0x01  # NFC Forum well-known type

    header = (mb << 7) | (me << 6) | (cf << 5) | (sr << 4) | (il << 3) | tnf

    record = bytearray([header, len(type_bytes)])
    if sr:
        record.append(len(payload))
    else:
        record.extend(len(payload).to_bytes(4, byteorder="big"))

    record.extend(type_bytes)
    record.extend(payload)
    return bytes(record)


def build_vcard_record(
    full_name: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    organization: Optional[str] = None,
    title: Optional[str] = None,
    url: Optional[str] = None,
    note: Optional[str] = None,
    is_first: bool = True,
    is_last: bool = True,
) -> bytes:
    """Build an NDEF MIME-type 'text/vcard' record for iOS/Android Contacts."""
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{full_name}",
    ]
    # Name parts (Last;First;Middle;Prefix;Suffix)
    name_parts = full_name.split(maxsplit=1)
    if len(name_parts) == 2:
        lines.append(f"N:{name_parts[1]};{name_parts[0]};;;")
    else:
        lines.append(f"N:{full_name};;;;")

    if organization:
        lines.append(f"ORG:{organization}")
    if title:
        lines.append(f"TITLE:{title}")
    if phone:
        # Clean phone
        lines.append(f"TEL;TYPE=CELL,VOICE:{phone}")
    if email:
        lines.append(f"EMAIL;TYPE=INTERNET,WORK:{email}")
    if url:
        lines.append(f"URL:{url}")
    if note:
        lines.append(f"NOTE:{note}")

    lines.append("END:VCARD")
    vcard_payload = "\r\n".join(lines).encode("utf-8")

    type_bytes = b"text/vcard"

    mb = 1 if is_first else 0
    me = 1 if is_last else 0
    cf = 0
    sr = 1 if len(vcard_payload) <= 255 else 0
    il = 0
    tnf = 0x02  # MIME media type

    header = (mb << 7) | (me << 6) | (cf << 5) | (sr << 4) | (il << 3) | tnf

    record = bytearray([header, len(type_bytes)])
    if sr:
        record.append(len(vcard_payload))
    else:
        record.extend(len(vcard_payload).to_bytes(4, byteorder="big"))

    record.extend(type_bytes)
    record.extend(vcard_payload)
    return bytes(record)


def wrap_in_ndef_tlv(ndef_message: bytes) -> bytes:
    """Wrap raw NDEF message bytes into an NFC Forum Type 2 TLV block."""
    tlv = bytearray()
    tlv.append(0x03)  # NDEF Message TLV Type

    length = len(ndef_message)
    if length < 255:
        tlv.append(length)
    else:
        # Extended format
        tlv.append(0xFF)
        tlv.extend(length.to_bytes(2, byteorder="big"))

    tlv.extend(ndef_message)
    tlv.append(0xFE)  # Terminator TLV
    return bytes(tlv)
