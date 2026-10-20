#!/usr/bin/env python3
"""Minimal dtbo image (dt_table_header) packer.

Matches what mkbootimg/mkdtimg produces for an Android DTBO partition:
all header and entry fields are big-endian (fdt32), the DTBs follow the
entry table contiguously.
"""
import argparse
import struct
import sys

DT_TABLE_MAGIC = 0xD7B7AB1E
HEADER_SIZE = 32
ENTRY_SIZE = 32


def main():
    p = argparse.ArgumentParser()
    p.add_argument("dtbs", nargs="+", help="one or more .dtbo/.dtb files")
    p.add_argument("--page_size", type=int, default=4096)
    p.add_argument("--version", type=int, default=0)
    p.add_argument("-o", "--output", required=True)
    a = p.parse_args()

    blobs = [open(f, "rb").read() for f in a.dtbs]
    for f, b in zip(a.dtbs, blobs):
        if b[:4] != b"\xd0\x0d\xfe\xed":
            print("warning: %s does not start with the FDT magic" % f, file=sys.stderr)

    entries_offset = HEADER_SIZE
    data_offset = entries_offset + ENTRY_SIZE * len(blobs)

    entries = b""
    body = b""
    off = data_offset
    for b in blobs:
        # dtb_size, dtb_offset, id, rev, custom[0..3]
        entries += struct.pack(">2I6I", len(b), off, 0, 0, 0, 0, 0, 0)
        body += b
        off += len(b)

    total = data_offset + len(body)

    header = struct.pack(
        ">8I",
        DT_TABLE_MAGIC,
        total,
        HEADER_SIZE,
        ENTRY_SIZE,
        len(blobs),
        entries_offset,
        a.page_size,
        a.version,
    )

    with open(a.output, "wb") as f:
        f.write(header + entries + body)
    print("wrote %s (%d bytes, %d entries)" % (a.output, total, len(blobs)))


if __name__ == "__main__":
    main()
