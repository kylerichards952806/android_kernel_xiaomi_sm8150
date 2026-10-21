#!/usr/bin/env python3
"""Compare two arm64 kernel Images and say how they differ.

Built for one question: when our kernel will not boot and the vendor's will,
is the difference the source tree or the compiler? Comparing a control build
(vendor commit + vendor clang) against the stock image separates those, because
a control that matches stock means the remaining delta is our patches.

Reports the arm64 header field by field, then a 16-byte block match ratio and
the offsets where the two images first diverge. A raw arm64 Image is not
compressed, so this is a genuine byte comparison, not a hash of a wrapper.

    ./compare-kernels.py stock.img control/Image [--blocks 4096]
"""

import argparse
import hashlib
import os
import struct
import sys

HEADER = struct.Struct("<IIQQQQQQ")  # code0, code1, text_offset, image_size,
                                     # flags, res2, res3, res4
FIELDS = ("code0", "code1", "text_offset", "image_size", "flags", "res2", "res3", "res4")


def header(path):
    # The arm64 Image header is 64 bytes: the packed fields below (56 bytes)
    # followed by the 4-byte magic at offset 56 and a reserved word after it.
    with open(path, "rb") as f:
        raw = f.read(64)
    if len(raw) < 64:
        raise SystemExit(f"{path}: shorter than an arm64 image header")
    vals = HEADER.unpack(raw[:HEADER.size])
    magic = struct.unpack("<I", raw[56:60])[0]
    return dict(zip(FIELDS, vals)), magic


def code0_meaning(code0):
    # The first instruction is a branch past the header; its target is the
    # real entry point, so a mismatch here means a different linker layout.
    if code0 & 0xFC000000 == 0x14000000:
        return f"b {((code0 & 0x03FFFFFF) << 2)}"
    return f"0x{code0:08x}"


def block_match(a, b, block):
    """Fraction of equal blocks over the overlapping range, plus the ratio of
    total bytes that match. Both images being the same size is the norm."""
    n = min(len(a), len(b))
    same = 0
    for off in range(0, n - block + 1, block):
        if a[off:off + block] == b[off:off + block]:
            same += 1
    total = max(1, n // block)
    return same, total, same / total


def regions(a, b, block, limit):
    """Contiguous ranges of differing blocks, as (start, end) offsets."""
    out = []
    n = min(len(a), len(b))
    cur = None
    for off in range(0, n - block + 1, block):
        differs = a[off:off + block] != b[off:off + block]
        if differs and cur is None:
            cur = off
        elif not differs and cur is not None:
            out.append((cur, off))
            cur = None
            if len(out) >= limit:
                return out
    if cur is not None:
        out.append((cur, n))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--blocks", type=int, default=4096,
                    help="block size in bytes for the match ratio (default 4096)")
    ap.add_argument("--show", type=int, default=12, help="differing regions to list")
    args = ap.parse_args()

    da, db = open(args.a, "rb").read(), open(args.b, "rb").read()

    print(f"A: {args.a}  {len(da):,} B  sha256 {hashlib.sha256(da).hexdigest()[:16]}")
    print(f"B: {args.b}  {len(db):,} B  sha256 {hashlib.sha256(db).hexdigest()[:16]}")

    print("\nheader")
    ha, ma = header(args.a)
    hb, mb = header(args.b)
    for k in FIELDS:
        va, vb = ha[k], hb[k]
        mark = "same" if va == vb else "DIFF"
        extra = f"  ({code0_meaning(va)!s})" if k == "code0" else ""
        print(f"  {k:<12} {va:#018x}  {vb:#018x}  {mark}{extra}")
    print(f"  {'magic':<12} {'ARMd' if ma == 0x644d5241 else hex(ma)}"
          f"  {'ARMd' if mb == 0x644d5241 else hex(mb)}")

    if ha["image_size"] != len(da) or hb["image_size"] != len(db):
        print("\n  note: image_size does not equal the file size in at least one image")
        print(f"        A header {ha['image_size']:,} vs file {len(da):,}")
        print(f"        B header {hb['image_size']:,} vs file {len(db):,}")

    if len(da) != len(db):
        print(f"\nsize differs by {len(db) - len(da):+,} bytes")

    same, total, ratio = block_match(da, db, args.blocks)
    print(f"\nbyte match: {same:,}/{total:,} blocks of {args.blocks} B equal "
          f"({ratio:.1%}); {len(da) - len(db):+d} B length delta")

    diff = regions(da, db, args.blocks, args.show)
    if not diff:
        print("no differing block inside the overlapping range")
    else:
        print(f"\nfirst differing regions (up to {args.show}):")
        for start, end in diff:
            print(f"  0x{start:08x} .. 0x{end:08x}  ({end - start:,} B)")
            print(f"    A {da[start:start+16].hex(' ')}")
            print(f"    B {db[start:start+16].hex(' ')}")

    if da == db:
        print("\nthe two images are byte-identical")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
