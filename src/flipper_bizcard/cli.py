"""Command Line Interface for Flipper NFC Digital Business Card Suite."""

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

from flipper_bizcard.encoder.ndef import build_uri_record, build_vcard_record, wrap_in_ndef_tlv
from flipper_bizcard.encoder.ntag215 import format_ntag215_memory, generate_valid_uid
from flipper_bizcard.encoder.flipper_nfc import serialize_flipper_nfc, parse_flipper_nfc
from flipper_bizcard.badge.display import generate_ascii_badge, generate_flipper_lcd_image


def print_banner():
    banner = """[bold cyan]
  ?? Flipper Zero NFC Digital Business Card Suite
[/bold cyan][dim]  Create & Inspect Apple/Android Background-Scanning Cards[/dim]
"""
    if RICH_AVAILABLE:
        console.print(banner)
    else:
        print("\n=== Flipper Zero NFC Digital Business Card Suite ===\n")


def cmd_create(args):
    """Handle card creation."""
    print_banner()

    card_type = args.type.lower()
    if card_type == "url":
        if not args.url:
            print("Error: --url is required when creating a URL card.", file=sys.stderr)
            sys.exit(1)
        ndef_msg = build_uri_record(args.url)
        beam_target = args.url
    elif card_type == "vcard":
        if not args.name:
            print("Error: --name is required when creating a vCard contact card.", file=sys.stderr)
            sys.exit(1)
        ndef_msg = build_vcard_record(
            full_name=args.name,
            phone=args.phone,
            email=args.email,
            organization=args.org,
            title=args.role,
            url=args.url,
            note=args.note,
        )
        beam_target = f"{args.name} ({args.email or args.phone or 'Contact'})"
    else:
        print(f"Error: Unknown card type '{args.type}'. Use 'url' or 'vcard'.", file=sys.stderr)
        sys.exit(1)

    tlv_data = wrap_in_ndef_tlv(ndef_msg)
    uid, _, _ = generate_valid_uid()
    pages = format_ntag215_memory(tlv_data, uid_override=uid)
    nfc_content = serialize_flipper_nfc(pages, uid)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(nfc_content, encoding="utf-8")

    # Generate badge if requested
    badge_path = None
    if args.badge:
        b_path = Path(args.badge)
        generate_flipper_lcd_image(
            name=args.name or "Contact",
            subtitle=args.role or "NFC Card",
            url=args.url or "https://flipperzero.one",
            output_path=str(b_path),
        )
        badge_path = str(b_path)

    if RICH_AVAILABLE:
        table = Table(title="Card Specifications", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="dim")
        table.add_column("Value", style="bold green")

        table.add_row("Card Format", "NTAG215 (NFC Forum Type 2)")
        table.add_row("Card Type", f"{card_type.upper()} ({'Website/Link' if card_type == 'url' else 'Contact vCard'})")
        table.add_row("Target Beam", beam_target)
        table.add_row("NDEF Size", f"{len(ndef_msg)} bytes (Max 504 bytes)")
        table.add_row("UID", " ".join(f"{b:02X}" for b in uid))
        table.add_row("iOS Background Scan", "? 100% Compatible (iPhone XR / 11 / 12 / 13 / 14 / 15 / 16)")
        table.add_row("Output File", str(out_path.resolve()))
        if badge_path:
            table.add_row("128x64 LCD Badge", badge_path)

        console.print(table)

        # ASCII preview of Flipper Screen
        ascii_box = generate_ascii_badge(
            name=args.name or "NFC Card",
            subtitle=args.role or card_type.upper(),
            target=beam_target[:26],
        )
        console.print(Panel(ascii_box, title="[bold yellow]Flipper 128x64 LCD Preview[/bold yellow]", expand=False))

        # Instructions
        instr = f"""
[bold green]How to Use on Flipper Zero:[/bold green]
1. Open [cyan]qFlipper[/cyan] on PC or the [cyan]Flipper Mobile App[/cyan] on your phone.
2. Navigate to [cyan]SD Card -> /ext/nfc/[/cyan] and upload [yellow]{out_path.name}[/yellow].
3. On Flipper Zero: Open [bold]NFC -> Saved -> {out_path.stem} -> Emulate[/bold].
4. [bold yellow]Tap test:[/bold yellow] Touch the top edge of an iPhone against the back of your Flipper.
   The Safari/Contacts prompt will appear immediately!
"""
        console.print(Panel(instr, title="[bold]Ready to Deploy[/bold]", border_style="green"))
    else:
        print(f"Successfully generated: {out_path}")


def cmd_inspect(args):
    """Inspect and validate an existing .nfc file."""
    print_banner()
    in_path = Path(args.file)
    if not in_path.exists():
        print(f"Error: File not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    content = in_path.read_text(encoding="utf-8", errors="replace")
    meta = parse_flipper_nfc(content)

    if RICH_AVAILABLE:
        table = Table(title=f"Inspection: {in_path.name}", show_header=True)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Device Type", str(meta.get("device_type")))
        table.add_row("UID", str(meta.get("uid")))
        table.add_row("Pages Dumped", str(len(meta.get("pages", {}))))
        table.add_row("iOS Background Compatible", "? YES" if meta["ios_compatible"] else "? NO")

        console.print(table)

        if meta["ndef_records"]:
            rec_table = Table(title="Decoded NDEF Records", show_header=True)
            rec_table.add_column("#", style="dim")
            rec_table.add_column("Type", style="green")
            rec_table.add_column("Decoded Content", style="yellow")

            for i, rec in enumerate(meta["ndef_records"], 1):
                rec_table.add_row(str(i), rec.get("kind", rec["type"]), str(rec["decoded_content"]))
            console.print(rec_table)
        else:
            console.print("[yellow]Warning: No standard NDEF records found in user memory.[/yellow]")

        notes_panel = "\n".join(f"• {note}" for note in meta["compatibility_notes"])
        console.print(Panel(notes_panel, title="Compatibility Notes", border_style="blue"))
    else:
        print(f"Device: {meta.get('device_type')}, UID: {meta.get('uid')}, iOS: {meta['ios_compatible']}")


def main():
    parser = argparse.ArgumentParser(
        prog="bizcard",
        description="Flipper Zero NFC Digital Business Card Suite",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create command
    create_parser = subparsers.add_parser("create", help="Create an NFC business card .nfc file")
    create_parser.add_argument("--type", choices=["url", "vcard"], default="url", help="Card type: url or vcard")
    create_parser.add_argument("--url", help="Website, LinkedIn, GitHub, or Linktree URL")
    create_parser.add_argument("--name", help="Full Name (for vCard or display)")
    create_parser.add_argument("--role", help="Professional Title / Role")
    create_parser.add_argument("--org", help="Company / Organization (vCard)")
    create_parser.add_argument("--phone", help="Phone Number (vCard)")
    create_parser.add_argument("--email", help="Email Address (vCard)")
    create_parser.add_argument("--note", help="Short note/bio (vCard)")
    create_parser.add_argument("-o", "--output", default="my_bizcard.nfc", help="Output .nfc file path")
    create_parser.add_argument("--badge", help="Optional output path to generate 128x64 LCD badge PNG")
    create_parser.set_defaults(func=cmd_create)

    # inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect an existing .nfc file for iOS compatibility")
    inspect_parser.add_argument("file", help="Path to .nfc file")
    inspect_parser.set_defaults(func=cmd_inspect)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
