"""Unit tests for Flipper NFC Digital Business Card encoder and parser using standard unittest."""

import unittest
from flipper_bizcard.encoder.ndef import build_uri_record, build_vcard_record, wrap_in_ndef_tlv
from flipper_bizcard.encoder.ntag215 import format_ntag215_memory, generate_valid_uid, TOTAL_PAGES
from flipper_bizcard.encoder.flipper_nfc import serialize_flipper_nfc, parse_flipper_nfc


class TestFlipperNfcCard(unittest.TestCase):

    def test_uri_record_prefix_compression(self):
        record = build_uri_record("https://github.com/example")
        self.assertTrue(record[0] & 0x80)  # MB
        self.assertTrue(record[0] & 0x40)  # ME
        self.assertEqual(record[1], 1)     # Type length
        self.assertEqual(record[3], ord("U"))  # Type 'U'
        self.assertEqual(record[4], 0x04)      # 0x04 is 'https://' prefix code
        self.assertEqual(record[5:].decode("utf-8"), "github.com/example")

    def test_vcard_record_structure(self):
        record = build_vcard_record(
            full_name="Jane Doe",
            phone="+15550192834",
            email="jane.doe@example.com",
            title="Software Engineer"
        )
        self.assertIn(b"text/vcard", record)
        self.assertIn(b"BEGIN:VCARD", record)
        self.assertIn(b"FN:Jane Doe", record)
        self.assertIn(b"TEL;TYPE=CELL,VOICE:+15550192834", record)
        self.assertIn(b"END:VCARD", record)

    def test_wrap_in_ndef_tlv(self):
        dummy = b"\x01\x02\x03"
        tlv = wrap_in_ndef_tlv(dummy)
        self.assertEqual(tlv[0], 0x03)       # TLV Type NDEF
        self.assertEqual(tlv[1], len(dummy))
        self.assertEqual(tlv[2:5], dummy)
        self.assertEqual(tlv[-1], 0xFE)      # Terminator TLV

    def test_ntag215_memory_pages(self):
        tlv = wrap_in_ndef_tlv(build_uri_record("https://example.com"))
        uid, bcc0, bcc1 = generate_valid_uid()
        pages = format_ntag215_memory(tlv, uid_override=uid)

        self.assertEqual(len(pages), TOTAL_PAGES)
        self.assertEqual(pages[0][0], 0x04)
        self.assertEqual(pages[0][3], bcc0)
        self.assertEqual(pages[2][0], bcc1)
        self.assertEqual(pages[3], bytes([0xE1, 0x10, 0x6D, 0x00]))
        self.assertEqual(pages[4][0], 0x03)

    def test_flipper_nfc_roundtrip(self):
        url = "https://linkedin.com/in/example"
        tlv = wrap_in_ndef_tlv(build_uri_record(url))
        uid, _, _ = generate_valid_uid()
        pages = format_ntag215_memory(tlv, uid_override=uid)
        nfc_text = serialize_flipper_nfc(pages, uid)

        # Check official Flipper v4 headers
        self.assertIn("Filetype: Flipper NFC device", nfc_text)
        self.assertIn("Device type: NTAG/Ultralight", nfc_text)
        self.assertIn("NTAG/Ultralight type: NTAG215", nfc_text)
        self.assertIn("Pages total: 135", nfc_text)
        self.assertIn("Pages read: 135", nfc_text)

        # Parse back
        meta = parse_flipper_nfc(nfc_text)
        self.assertEqual(meta["device_type"], "NTAG/Ultralight")
        self.assertEqual(meta["ntag_type"], "NTAG215")
        self.assertTrue(meta["ios_compatible"])
        self.assertEqual(len(meta["ndef_records"]), 1)
        self.assertEqual(meta["ndef_records"][0]["decoded_content"], url)


if __name__ == "__main__":
    unittest.main()