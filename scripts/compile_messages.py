"""
Compile all .po translation files to binary .mo files.

Run this whenever you add or change translations:
    python scripts/compile_messages.py

No external tools required - uses a pure-Python .mo writer.
"""

import struct
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "locales"


def parse_po(po_path: Path) -> dict[str, str]:
    """Parse a .po file and return {msgid: msgstr} (non-empty translations only)."""
    catalog: dict[str, str] = {}
    msgid = ""
    msgstr = ""
    in_msgid = False
    in_msgstr = False

    def flush():
        nonlocal msgid, msgstr, in_msgid, in_msgstr
        # Decode escape sequences (\n, \t, \\)
        def unescape(s: str) -> str:
            return s.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")

        if msgstr:
            catalog[unescape(msgid)] = unescape(msgstr)
        msgid = msgstr = ""
        in_msgid = in_msgstr = False

    with open(po_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")

            if line.startswith("#") or line.startswith("msgctxt"):
                flush()
                continue

            if line.startswith('msgid "'):
                flush()
                msgid = line[7:-1]
                in_msgid = True
                in_msgstr = False

            elif line.startswith('msgstr "'):
                msgstr = line[8:-1]
                in_msgid = False
                in_msgstr = True

            elif line.startswith('"'):
                fragment = line[1:-1]
                if in_msgid:
                    msgid += fragment
                elif in_msgstr:
                    msgstr += fragment

            elif line.strip() == "":
                flush()

    flush()
    # Keep the header entry (empty msgid) so gettext knows the charset is UTF-8.
    # Removing it causes UnicodeDecodeError when the .mo is loaded on systems
    # whose default encoding is not UTF-8 (e.g. Windows with ASCII locale).
    return catalog


def write_mo(catalog: dict[str, str], mo_path: Path) -> None:
    """Write a binary gettext .mo file (little-endian, no hash table)."""
    keys = sorted(catalog.keys())
    n = len(keys)

    # File layout:
    #   28 bytes header
    #   n * 8  bytes original-string offset table
    #   n * 8  bytes translated-string offset table
    #   string data (all msgids then all msgstrs, each null-terminated)
    HEADER_SZ = 28
    strings_start = HEADER_SZ + n * 16  # header + two tables

    orig_ids = [k.encode("utf-8") for k in keys]
    orig_strs = [catalog[k].encode("utf-8") for k in keys]

    orig_table: list[tuple[int, int]] = []
    trans_table: list[tuple[int, int]] = []
    data = bytearray()
    cur = strings_start

    for s in orig_ids:
        orig_table.append((len(s), cur))
        data.extend(s + b"\x00")
        cur += len(s) + 1

    for s in orig_strs:
        trans_table.append((len(s), cur))
        data.extend(s + b"\x00")
        cur += len(s) + 1

    with open(mo_path, "wb") as f:
        # Header
        f.write(struct.pack("<7I",
            0x950412de,          # magic
            0,                   # revision
            n,                   # number of strings
            HEADER_SZ,           # offset of orig table
            HEADER_SZ + n * 8,   # offset of trans table
            0,                   # hash table size (disabled)
            0,                   # hash table offset
        ))
        for length, offset in orig_table:
            f.write(struct.pack("<II", length, offset))
        for length, offset in trans_table:
            f.write(struct.pack("<II", length, offset))
        f.write(bytes(data))


def main() -> None:
    po_files = list(LOCALES_DIR.rglob("*.po"))
    if not po_files:
        print("No .po files found under", LOCALES_DIR)
        return

    for po_path in po_files:
        mo_path = po_path.with_suffix(".mo")
        print(f"Compiling {po_path.relative_to(LOCALES_DIR.parent)} ...", end=" ")
        catalog = parse_po(po_path)
        write_mo(catalog, mo_path)
        print(f"done  ({len(catalog)} strings -> {mo_path.name})")


if __name__ == "__main__":
    main()
