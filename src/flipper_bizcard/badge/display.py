"""Flipper Zero 128x64 LCD Badge & QR Fallback Generator."""

import io
from typing import Optional

try:
    import qrcode
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def generate_ascii_badge(name: str, subtitle: str, target: str) -> str:
    """Generate a 128x64 aspect text preview for terminal display."""
    width = 46
    border = "+" + "-" * (width - 2) + "+"
    empty = "|" + " " * (width - 2) + "|"

    def pad_line(text: str) -> str:
        truncated = text[: width - 6]
        padded = f"  {truncated}".ljust(width - 2)
        return f"|{padded}|"

    lines = [
        border,
        "|  ?? FLIPPER ZERO NFC BADGE" + " " * (width - 30) + "|",
        border,
        empty,
        pad_line(f"NAME: {name}"),
        pad_line(f"ROLE: {subtitle}"),
        pad_line(f"BEAM: {target}"),
        empty,
        "|  [Tap back of iPhone to beam]" + " " * (width - 34) + "|",
        border,
    ]
    return "\n".join(lines)


def generate_flipper_lcd_image(
    name: str,
    subtitle: str,
    url: str,
    output_path: Optional[str] = None
) -> Optional[bytes]:
    """Generate a genuine 128x64 1-bit monochrome PNG compatible with Flipper LCD."""
    if not PIL_AVAILABLE:
        return None

    # Flipper Zero LCD Dimensions
    width, height = 128, 64
    img = Image.new("1", (width, height), color=1)  # 1 = White background
    draw = ImageDraw.Draw(img)

    # Generate small QR code (version 1 or 2, minimal border)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=0, back_color=1).convert("1")

    # Resize QR to fit nicely on the right (e.g. 48x48)
    qr_size = min(48, qr_img.width)
    qr_img = qr_img.resize((qr_size, qr_size))
    qr_x = width - qr_size - 4
    qr_y = (height - qr_size) // 2
    img.paste(qr_img, (qr_x, qr_y))

    # Outer decorative frame
    draw.rectangle([1, 1, width - 2, height - 2], outline=0, width=1)
    draw.rectangle([3, 3, width - 4, height - 4], outline=0, width=1)

    # Use default bitmap font
    font = ImageFont.load_default()

    # Left text info
    draw.text((7, 8), "?? BIZCARD", fill=0, font=font)
    draw.line([(7, 19), (qr_x - 4, 19)], fill=0, width=1)

    # Name and subtitle
    draw.text((7, 24), name[:11], fill=0, font=font)
    draw.text((7, 36), subtitle[:11], fill=0, font=font)
    draw.text((7, 48), "NFC READY", fill=0, font=font)

    if output_path:
        img.save(output_path, "PNG")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
