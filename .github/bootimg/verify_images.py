#!/usr/bin/env python3
"""Sanity-check the boot.img and dtbo.img produced by the build.

Asserts the packaged boot image is a header v2 image laid out the way vayu
expects, that the kernel inside it is exactly the Image that was built, and
that the dtbo table is well formed.
"""
import os
import struct
import sys

dist = sys.argv[1] if len(sys.argv) > 1 else "dist"

BOOT_PARTITION = 134217728  # BOARD_BOOTIMAGE_PARTITION_SIZE

boot = open(os.path.join(dist, "boot.img"), "rb").read()
image = open(os.path.join(dist, "Image"), "rb").read()

assert boot[:8] == b"ANDROID!", "boot.img magic"
ks, ka, rs, ra, ss, sa, tags, page, hv, osv = struct.unpack_from("<10I", boot, 8)

assert hv == 2, "expected header_version 2, got %d" % hv
assert page == 4096, "page size %d" % page
assert (ka, ra, tags, sa) == (0x8000, 0x1000000, 0x100, 0), \
    "addresses %r" % ((ka, ra, tags, sa),)
assert ks == len(image), "kernel size %d != Image %d" % (ks, len(image))
assert boot[page:page + ks] == image, "embedded kernel != built Image"

cmdline = boot[0x40:0x240].rstrip(b"\x00")
assert b"androidboot.hardware=qcom" in cmdline, cmdline[:60]

size = page + ((ks + page - 1) // page) * page + ((rs + page - 1) // page) * page
assert size <= BOOT_PARTITION, "boot.img %d exceeds the 128 MiB partition" % size

# The image must be the whole partition and must still carry the vendor's AVB
# footer: the bootloader rejects images without it (AUDIT.md section 7), so a
# truncated or re-signed image has to fail here rather than at the device.
assert len(boot) == BOOT_PARTITION, \
    "boot.img is %d bytes, expected the full %d-byte partition" % (len(boot), BOOT_PARTITION)
assert boot[-64:-60] == b"AVBf", "boot.img is missing the AVB footer"

print("boot.img ok: header v%d, %d bytes, kernel %d, ramdisk %d, avb footer present"
      % (hv, len(boot), ks, rs))

dtbo_path = os.path.join(dist, "dtbo.img")
dtbo = open(dtbo_path, "rb").read()
magic, total, hsize, esize, ecount, eoff, dpage, ver = struct.unpack_from(">8I", dtbo, 0)

assert magic == 0xD7B7AB1E, "dtbo magic 0x%08x" % magic
assert ecount >= 1, "no dtbo entries"
assert total == len(dtbo), "dtbo total_size %d != file size %d" % (total, len(dtbo))

for i in range(ecount):
    dsize, doff = struct.unpack_from(">2I", dtbo, eoff + i * esize)
    assert doff + dsize <= total, "entry %d runs past the table" % i
    assert dtbo[doff:doff + 4] == b"\xd0\x0d\xfe\xed", "entry %d is not an FDT" % i

print("dtbo.img ok: %d entries, %d bytes" % (ecount, total))
