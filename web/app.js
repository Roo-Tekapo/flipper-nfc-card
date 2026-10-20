// Flipper Zero NFC Digital Business Card Engine (Pure Client-side JS)

let currentMode = "url";

const URI_PREFIXES = [
  { code: 0x01, prefix: "http://www." },
  { code: 0x02, prefix: "https://www." },
  { code: 0x03, prefix: "http://" },
  { code: 0x04, prefix: "https://" },
  { code: 0x05, prefix: "tel:" },
  { code: 0x06, prefix: "mailto:" }
];

function switchMode(mode) {
  currentMode = mode;
  document.getElementById("tab-url").classList.toggle("active", mode === "url");
  document.getElementById("tab-vcard").classList.toggle("active", mode === "vcard");
  document.getElementById("url-fields").style.display = mode === "url" ? "block" : "none";
  document.getElementById("vcard-fields").style.display = mode === "vcard" ? "block" : "none";

  const contactSheet = document.getElementById("ios-contact-sheet");
  if (contactSheet) {
    contactSheet.style.display = mode === "vcard" ? "block" : "none";
  }

  updatePreview();
}

function updatePreview() {
  const iosIcon = document.getElementById("ios-icon");
  const iosTitle = document.getElementById("ios-title");
  const iosSubtitle = document.getElementById("ios-subtitle");
  const lcdName = document.getElementById("lcd-name");
  const lcdSubtitle = document.getElementById("lcd-subtitle");
  const lcdExtra = document.getElementById("lcd-extra");

  if (currentMode === "url") {
    const url = document.getElementById("input-url").value.trim() || "https://github.com/yourusername";
    const name = document.getElementById("input-url-title").value.trim() || "Alex Doe";
    const subtitle = document.getElementById("input-url-subtitle").value.trim() || "Software Engineer";

    iosIcon.innerHTML = "&#127760;";
    iosIcon.style.background = "#007aff";
    iosTitle.textContent = "Website NFC Tag";
    iosSubtitle.textContent = `Open "${url}" in Safari`;

    lcdName.textContent = name;
    lcdSubtitle.textContent = subtitle;
    lcdExtra.innerHTML = "&#128225; Ready to beam link";
  } else {
    const name = document.getElementById("input-vcard-name").value.trim() || "Alex Doe";
    const role = document.getElementById("input-vcard-role").value.trim() || "Full Stack Developer";
    const org = document.getElementById("input-vcard-org").value.trim() || "Tech Studio";
    const phone = document.getElementById("input-vcard-phone").value.trim() || "+1 (555) 019-2834";
    const email = document.getElementById("input-vcard-email").value.trim() || "alex.doe@example.com";
    const url = document.getElementById("input-vcard-url").value.trim() || "https://github.com/yourusername";
    const note = document.getElementById("input-vcard-note") ? document.getElementById("input-vcard-note").value.trim() : "Met via Flipper NFC";

    iosIcon.innerHTML = "&#128100;";
    iosIcon.style.background = "#34c759";
    iosTitle.textContent = "Contact Card";
    iosSubtitle.textContent = `Add "${name}${org ? ' - ' + org : ''}" to Contacts`;

    // Update Flipper LCD
    lcdName.textContent = name;
    lcdSubtitle.textContent = role;
    lcdExtra.textContent = org ? org.slice(0, 16) : "vCard Contact";

    // Update Expanded iOS Sheet Preview
    const avatarEl = document.getElementById("sheet-avatar");
    const sheetNameEl = document.getElementById("sheet-name");
    const sheetHeadlineEl = document.getElementById("sheet-headline");
    const sheetPhoneEl = document.getElementById("sheet-phone");
    const sheetEmailEl = document.getElementById("sheet-email");
    const sheetUrlEl = document.getElementById("sheet-url");
    const sheetNoteEl = document.getElementById("sheet-note");

    if (avatarEl) avatarEl.textContent = name.charAt(0).toUpperCase() || "A";
    if (sheetNameEl) sheetNameEl.textContent = name;
    if (sheetHeadlineEl) {
      sheetHeadlineEl.textContent = [role, org].filter(Boolean).join(" • ") || "Contact";
    }
    if (sheetPhoneEl) sheetPhoneEl.textContent = phone;
    if (sheetEmailEl) sheetEmailEl.textContent = email;
    if (sheetUrlEl) sheetUrlEl.textContent = url;
    if (sheetNoteEl) sheetNoteEl.textContent = note;
  }
}

// Attach event listeners to all inputs
document.querySelectorAll("input").forEach((inp) => {
  inp.addEventListener("input", updatePreview);
});

// Build NDEF URI Record
function buildNdefUriRecord(url) {
  let prefixCode = 0x00;
  let suffix = url;

  for (const item of URI_PREFIXES) {
    if (url.startsWith(item.prefix)) {
      prefixCode = item.code;
      suffix = url.slice(item.prefix.length);
      break;
    }
  }

  const encoder = new TextEncoder();
  const suffixBytes = encoder.encode(suffix);
  const payload = new Uint8Array(1 + suffixBytes.length);
  payload[0] = prefixCode;
  payload.set(suffixBytes, 1);

  const typeBytes = encoder.encode("U");
  const sr = payload.length <= 255;
  const header = 0xd1; // MB=1, ME=1, SR=1, TNF=1

  const record = [header, typeBytes.length, payload.length];
  record.push(...typeBytes);
  record.push(...payload);
  return new Uint8Array(record);
}

// Build NDEF vCard Record
function buildNdefVCardRecord(name, role, org, phone, email, url, note) {
  const lines = [
    "BEGIN:VCARD",
    "VERSION:3.0",
    `FN:${name}`
  ];

  const parts = name.split(" ");
  if (parts.length >= 2) {
    lines.push(`N:${parts.slice(1).join(" ")};${parts[0]};;;`);
  } else {
    lines.push(`N:${name};;;;`);
  }

  if (org) lines.push(`ORG:${org}`);
  if (role) lines.push(`TITLE:${role}`);
  if (phone) lines.push(`TEL;TYPE=CELL,VOICE:${phone}`);
  if (email) lines.push(`EMAIL;TYPE=INTERNET,WORK:${email}`);
  if (url) lines.push(`URL:${url}`);
  if (note) lines.push(`NOTE:${note}`);
  lines.push("END:VCARD");

  const vcardText = lines.join("\r\n");
  const encoder = new TextEncoder();
  const payload = encoder.encode(vcardText);
  const typeBytes = encoder.encode("text/vcard");

  const sr = payload.length <= 255;
  const header = sr ? 0xd2 : 0xc2; // MB=1, ME=1, SR, TNF=2 (MIME)

  const record = [header, typeBytes.length];
  if (sr) {
    record.push(payload.length);
  } else {
    record.push((payload.length >> 24) & 0xff);
    record.push((payload.length >> 16) & 0xff);
    record.push((payload.length >> 8) & 0xff);
    record.push(payload.length & 0xff);
  }

  record.push(...typeBytes);
  record.push(...payload);
  return new Uint8Array(record);
}

// Wrap in NDEF TLV
function wrapInNdefTlv(ndefMessage) {
  const len = ndefMessage.length;
  const tlv = [0x03]; // NDEF Message Type

  if (len < 255) {
    tlv.push(len);
  } else {
    tlv.push(0xff);
    tlv.push((len >> 8) & 0xff);
    tlv.push(len & 0xff);
  }

  tlv.push(...ndefMessage);
  tlv.push(0xfe); // Terminator TLV
  return new Uint8Array(tlv);
}

// Generate NTAG215 135 Pages
function formatNtag215(tlvData) {
  const totalPages = 135;
  const pages = [];

  // Generate random 7-byte UID starting with 0x04 (NXP)
  const uid = [0x04];
  for (let i = 0; i < 6; i++) {
    uid.push(Math.floor(Math.random() * 256));
  }

  const bcc0 = 0x88 ^ uid[0] ^ uid[1] ^ uid[2];
  const bcc1 = uid[3] ^ uid[4] ^ uid[5] ^ uid[6];

  // Page 0: UID0..2 + BCC0
  pages[0] = [uid[0], uid[1], uid[2], bcc0];
  // Page 1: UID3..6
  pages[1] = [uid[3], uid[4], uid[5], uid[6]];
  // Page 2: BCC1, Internal (0x48), Lock (0x00, 0x00)
  pages[2] = [bcc1, 0x48, 0x00, 0x00];
  // Page 3: CC Container (E1 10 6D 00)
  pages[3] = [0xe1, 0x10, 0x6d, 0x00];

  // User memory: Pages 4 through 129 (126 pages * 4 = 504 bytes)
  const userBytes = new Uint8Array(504);
  userBytes.set(tlvData.subarray(0, Math.min(tlvData.length, 504)));

  for (let p = 4; p <= 129; p++) {
    const offset = (p - 4) * 4;
    pages[p] = [
      userBytes[offset],
      userBytes[offset + 1],
      userBytes[offset + 2],
      userBytes[offset + 3]
    ];
  }

  // Dynamic lock and CFG pages
  pages[130] = [0x00, 0x00, 0x00, 0xbd];
  pages[131] = [0x04, 0x00, 0x00, 0xff];
  pages[132] = [0x00, 0x05, 0x00, 0x00];
  pages[133] = [0xff, 0xff, 0xff, 0xff];
  pages[134] = [0x00, 0x00, 0x00, 0x00];

  return { uid, pages };
}

// Serialize to official Flipper v4 NTAG/Ultralight .nfc format
function serializeToFlipperNfc(uid, pages) {
  const uidStr = uid.map((b) => b.toString(16).padStart(2, "0").toUpperCase()).join(" ");
  const lines = [
    "Filetype: Flipper NFC device",
    "Version: 4",
    "# Device type can be ISO14443-3A, ISO14443-3B, ISO14443-4A, ISO14443-4B, ISO15693-3, FeliCa, NTAG/Ultralight, Mifare Classic, Mifare Plus, Mifare DESFire, SLIX, ST25TB",
    "Device type: NTAG/Ultralight",
    "# UID is common for all formats",
    `UID: ${uidStr}`,
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
    `Pages total: ${pages.length}`,
    `Pages read: ${pages.length}`
  ];

  for (let i = 0; i < pages.length; i++) {
    const pageHex = pages[i].map((b) => b.toString(16).padStart(2, "0").toUpperCase()).join(" ");
    lines.push(`Page ${i}: ${pageHex}`);
  }

  lines.push("Failed authentication attempts: 0");
  return lines.join("\n") + "\n";
}

function generateAndDownloadNFC() {
  let ndefMessage;
  let filename = "my_bizcard.nfc";

  if (currentMode === "url") {
    const url = document.getElementById("input-url").value.trim();
    if (!url) {
      alert("Please enter a destination URL!");
      return;
    }
    ndefMessage = buildNdefUriRecord(url);
    const cleanName = (document.getElementById("input-url-title").value.trim() || "link_card").toLowerCase().replace(/[^a-z0-9_]/g, "_");
    filename = `${cleanName}.nfc`;
  } else {
    const name = document.getElementById("input-vcard-name").value.trim();
    if (!name) {
      alert("Please enter your Full Name for the vCard!");
      return;
    }
    const role = document.getElementById("input-vcard-role").value.trim();
    const org = document.getElementById("input-vcard-org").value.trim();
    const phone = document.getElementById("input-vcard-phone").value.trim();
    const email = document.getElementById("input-vcard-email").value.trim();
    const url = document.getElementById("input-vcard-url").value.trim();
    const note = document.getElementById("input-vcard-note") ? document.getElementById("input-vcard-note").value.trim() : "";

    ndefMessage = buildNdefVCardRecord(name, role, org, phone, email, url, note);
    const cleanName = name.toLowerCase().replace(/[^a-z0-9_]/g, "_");
    filename = `${cleanName}_vcard.nfc`;
  }

  const tlvData = wrapInNdefTlv(ndefMessage);
  if (tlvData.length > 504) {
    alert(`Payload too large (${tlvData.length} bytes / max 504 bytes). Please shorten the fields.`);
    return;
  }

  const { uid, pages } = formatNtag215(tlvData);
  const nfcContent = serializeToFlipperNfc(uid, pages);

  const blob = new Blob([nfcContent], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

updatePreview();