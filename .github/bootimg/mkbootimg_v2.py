#!/usr/bin/env python3
"""Minimal, dependency-free Android boot image (header v2) packer.

Used by the CI workflow so building boot.img needs no external tooling.
Header v2 is the format vayu actually uses (no vendor_boot partition).
"""
import argparse
import hashlib
import struct
import sys

MAGIC = b"ANDROID!"
HEADER_SIZE = 0x660  # magic..extra_cmdline for v2


def align(n, page):
    return (n + page - 1) // page * page


def build_id(kernel, ramdisk, second, os_version):
    """SHA1 over the payload, matching AOSP mkbootimg for header v2."""
    h = hashlib.sha1()
    h.update(kernel)
    h.update(struct.pack("<I", len(ramdisk)))
    h.update(ramdisk)
    h.update(struct.pack("<I", len(second)))
    h.update(second)
    h.update(struct.pack("<I", os_version))
    return h.digest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kernel", required=True)
    p.add_argument("--ramdisk", default="")
    p.add_argument("--second", default="")
    p.add_argument("--cmdline", default="")
    p.add_argument("--name", default="")
    p.add_argument("--base", type=lambda s: int(s, 0), default=0)
    p.add_argument("--kernel_offset", type=lambda s: int(s, 0), default=0x8000)
    p.add_argument("--ramdisk_offset", type=lambda s: int(s, 0), default=0x1000000)
    p.add_argument("--second_offset", type=lambda s: int(s, 0), default=0xF00000)
    p.add_argument("--tags_offset", type=lambda s: int(s, 0), default=0x100)
    p.add_argument("--pagesize", type=int, default=2048)
    p.add_argument("--header_version", type=int, default=2)
    p.add_argument("--os_version", type=lambda s: int(s, 0), default=0)
    p.add_argument("--pad_to", type=int, default=0)
    p.add_argument("-o", "--output", required=True)
    a = p.parse_args()

    if a.header_version != 2:
        sys.exit("this packer only implements header v2")

    kernel = open(a.kernel, "rb").read()
    ramdisk = open(a.ramdisk, "rb").read() if a.ramdisk else b""
    second = open(a.second, "rb").read() if a.second else b""
    page = a.pagesize

    if len(a.cmdline.encode()) > 512:
        sys.exit("cmdline too long for header v2 (max 512 bytes)")

    hdr = bytearray(HEADER_SIZE)
    struct.pack_into("<8s", hdr, 0, MAGIC)
    struct.pack_into("<I", hdr, 0x08, len(kernel))
    struct.pack_into("<I", hdr, 0x0C, a.base + a.kernel_offset)
    struct.pack_into("<I", hdr, 0x10, len(ramdisk))
    struct.pack_into("<I", hdr, 0x14, a.base + a.ramdisk_offset)
    struct.pack_into("<I", hdr, 0x18, len(second))
    struct.pack_into("<I", hdr, 0x1C, a.base + a.second_offset)
    struct.pack_into("<I", hdr, 0x20, a.base + a.tags_offset)
    struct.pack_into("<I", hdr, 0x24, page)
    struct.pack_into("<I", hdr, 0x28, a.header_version)
    struct.pack_into("<I", hdr, 0x2C, a.os_version)
    hdr[0x30:0x30 + 16] = a.name.encode()[:16].ljust(16, b"\x00")
    hdr[0x40:0x40 + 512] = a.cmdline.encode().ljust(512, b"\x00")
    hdr[0x240:0x240 + 32] = build_id(kernel, ramdisk, second, a.os_version)

    out = bytearray()
    out += bytes(hdr).ljust(page, b"\x00")
    out += kernel.ljust(align(len(kernel), page), b"\x00")
    if ramdisk:
        out += ramdisk.ljust(align(len(ramdisk), page), b"\x00")
    if second:
        out += second.ljust(align(len(second), page), b"\x00")

    if a.pad_to:
        if len(out) > a.pad_to:
            sys.exit("image is %d bytes, larger than --pad_to %d" % (len(out), a.pad_to))
        out = out.ljust(a.pad_to, b"\x00")

    open(a.output, "wb").write(out)
    print("wrote %s (%d bytes)" % (a.output, len(out)))


if __name__ == "__main__":
    main()
