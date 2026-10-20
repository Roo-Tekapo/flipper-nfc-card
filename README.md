# ?? Flipper Zero NFC Digital Business Card Suite

> Turn your Flipper Zero into a high-compatibility digital business card. Tap any iPhone or Android phone against your Flipper to instantly beam your portfolio, LinkedIn, GitHub, or full contact card into their address book—**no app required on their phone!**

---

## ?? How It Works

* **iPhone Background NFC Reading:** All iPhones from **iPhone XR / XS to iPhone 16** feature native background tag reading. When you emulate an **NTAG215** card containing standard **NDEF records**, iOS automatically pops up a banner:
  * ?? **URL Cards:** `"Open 'https://...' in Safari"`
  * ?? **vCard Cards:** `"Add 'Name' to Contacts"`
* **Android Reading:** Works natively on all NFC-enabled Android phones when the screen is unlocked.
* **100% Native to Flipper Zero:** Runs directly from the Flipper's microSD card (`/ext/nfc/`). No dev boards or firmware mods needed.

---

## ?? Quickstart: Web Studio (No Install Needed!)

You don't even need to use the command line to create your card:

1. Open `web/index.html` in any browser (Chrome, Edge, Safari, Firefox).
2. Choose **Website / Link** or **Contact vCard**.
3. Fill in your details and watch the **Live iPhone Simulation** and **Flipper LCD Display** update in real time.
4. Click **"Download Flipper .nfc File"**.

---

## ?? Python CLI

If you prefer using the command line:

### 1. Installation (Optional)
```bash
pip install -r requirements.txt
# Or install in editable mode:
pip install -e .
```

### 2. Create a URL / Portfolio Card
```bash
python -m flipper_bizcard create \
  --type url \
  --url "https://github.com/yourusername" \
  --name "Your Name" \
  --role "Software Engineer" \
  -o "my_portfolio.nfc"
```

### 3. Create a Full Contact vCard (Name, Phone, Email, Org)
```bash
python -m flipper_bizcard create \
  --type vcard \
  --name "Jane Doe" \
  --role "Lead Developer" \
  --org "Tech Studio" \
  --phone "+1 (555) 019-2834" \
  --email "jane@example.com" \
  --url "https://janedoe.dev" \
  -o "jane_contact.nfc"
```

### 4. Inspect & Validate an Existing `.nfc` File
```bash
python -m flipper_bizcard inspect my_portfolio.nfc
```

---

## ?? How to Load onto Flipper Zero

### Option A: Using qFlipper (USB Cable)
1. Plug your Flipper Zero into your PC via USB.
2. Open **qFlipper**.
3. Click the **File Manager** icon (folder icon).
4. Navigate to: `SD Card` -> `nfc`.
5. Drag and drop your `.nfc` file into this folder.

### Option B: Using the Flipper Mobile App (Bluetooth)
1. Open the **Flipper Mobile App** on your phone (paired via Bluetooth).
2. Go to **Hub** -> **File Manager** -> **SD Card** -> `nfc/`.
3. Tap **Upload** and select your `.nfc` file.

### Option C: MicroSD Card Reader
1. Eject the microSD card from your Flipper.
2. Insert into your computer and copy the `.nfc` file into the `nfc/` folder.
3. Reinsert into Flipper.

---

## ? How to Beam Your Card

1. On your Flipper Zero, open:
   ```
   [Main Menu] -> NFC -> Saved -> [Your Card] -> Emulate
   ```
2. The Flipper will show `Emulating NTAG215`.
3. **The Sweet Spot (Tap Technique):**
   * **iPhone:** Touch the **top edge** of the iPhone (next to the camera bump) against the **lower-middle back** of the Flipper.
   * **Android:** Touch the center back of the phone against the back of the Flipper.
4. The notification prompt will appear on their phone screen in under 1 second!

---

## ??? Project Structure

```
flipper-nfc-card/
+-- README.md                  # This guide
+-- requirements.txt           # Python dependencies (rich, qrcode, pillow)
+-- pyproject.toml             # Project package configuration
+-- src/
¦   +-- flipper_bizcard/
¦       +-- encoder/
¦       ¦   +-- ndef.py        # NDEF record compiler (URI, vCard, TLV)
¦       ¦   +-- ntag215.py     # 135-page NTAG215 memory formatter & CC container
¦       ¦   +-- flipper_nfc.py # Flipper .nfc file serializer & inspector
¦       +-- badge/
¦       ¦   +-- display.py     # 128x64 LCD badge generator
¦       +-- cli.py             # Rich terminal CLI
+-- web/
¦   +-- index.html             # Offline Web Studio
¦   +-- style.css              # Dark-mode glassmorphic interface
¦   +-- app.js                 # Pure client-side JS compiler
+-- examples/                  # Ready-to-load sample .nfc cards
¦   +-- github_profile.nfc
¦   +-- linkedin_profile.nfc
¦   +-- developer_contact.nfc
+-- tests/
    +-- test_encoder.py        # Automated test suite
```

---

## ?? Technical Specifications

* **Tag Standard:** NFC Forum Type 2 Tag (NXP NTAG215, ISO14443-3A).
* **Capability Container (Page 3):** `0xE1 0x10 0x6D 0x00` (Mapping Version 1.0, 504 bytes user memory, open read/write access).
* **NDEF Record Framing:** Short record (`SR=1`) and normal record support with well-known URI prefix compression (`0x04` for `https://`, `0x03` for `http://`, etc.) and MIME `text/vcard` formatting.
* **Compatibility:** Tested and verified with iOS 13–18 background tag reader and Android 10+.
