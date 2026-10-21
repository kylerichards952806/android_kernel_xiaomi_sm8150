#!/usr/bin/env python3
"""Build a flashable boot.img by splicing a kernel into the vendor template.

Why this exists instead of mkbootimg: vayu's bootloader refuses boot images
generated from scratch — even when every header field, the 128 MiB length and a
fresh AVB footer match the vendor image — but boots any image derived from the
vendor's own 128 MiB partition dump, including with a different kernel and a
different ramdisk. The vendor footer is left byte-identical, which is the only
shape that has booted on this device.

Measured, not assumed: see AUDIT.md section 7.

    ./splice_boot.py --template boot-template.img.gz --kernel out/.../Image -o dist/boot.img
"""

import argparse
import gzip
import hashlib
import struct
import sys

PAGE = 4096


def align(n, p=PAGE):
    return (n + p - 1) // p * p


def read_raw(path):
    """Read bytes as-is: a ramdisk is usually already gzip and must not be
    decompressed here, the bootloader hands it to init untouched."""
    with open(path, "rb") as f:
        return f.read()


def load(path):
    with open(path, "rb") as f:
        head = f.read(2)
    if head == b"\x1f\x8b":
        with gzip.open(path, "rb") as f:
            return f.read()
    with open(path, "rb") as f:
        return f.read()


def parse_header(d):
    if d[:8] != b"ANDROID!":
        raise SystemExit(f"template is not a boot image: magic {d[:8]!r}")
    kernel_size = struct.unpack("<I", d[8:12])[0]
    ramdisk_size = struct.unpack("<I", d[16:20])[0]
    page_size = struct.unpack("<I", d[36:40])[0]
    header_version = struct.unpack("<I", d[40:44])[0]
    return kernel_size, ramdisk_size, page_size, header_version


def footer_offset(d):
    """Offset of the vbmeta blob described by the 64-byte AVB footer, or None."""
    # The 64-byte footer starts 64 bytes before the end of the partition; the
    # magic is at its head, not at the file's last four bytes.
    if d[-64:-60] != b"AVBf":
        return None
    # Footer layout: magic(4) major(4) minor(4) original_image_size(8)
    # vbmeta_offset(8) vbmeta_size(8) reserved(28) — all integers big-endian.
    vbmeta_offset = struct.unpack(">Q", d[-64 + 20:-64 + 28])[0]
    return vbmeta_offset


def boot_id(kernel, ramdisk, second_size=0):
    """The boot header's id field: SHA1 over contents and their sizes."""
    h = hashlib.sha1()
    h.update(kernel)
    h.update(struct.pack("<I", len(kernel)))
    h.update(ramdisk)
    h.update(struct.pack("<I", len(ramdisk)))
    h.update(struct.pack("<I", second_size))
    return h.digest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True,
                    help="vendor boot image (128 MiB partition dump), optionally gzipped")
    ap.add_argument("--kernel", required=True, help="arm64 Image to splice in")
    ap.add_argument("--ramdisk-from", default=None,
                    help="boot image to take the ramdisk from instead of the "
                         "template's own (used for the Android 15 / LineageOS 22.2 "
                         "build, where the template is the newer 24.0 container)")
    ap.add_argument("--ramdisk", default=None,
                    help="raw ramdisk blob to use instead of the template's "
                         "(already-compressed cpio, e.g. the 22.2 ramdisk stored "
                         "in .github/bootimg)")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    template = bytearray(load(args.template))
    kernel = load(args.kernel)

    kernel_size, ramdisk_size, page_size, header_version = parse_header(template)
    if page_size != PAGE:
        raise SystemExit(f"template page_size is {page_size}, expected {PAGE}")
    if header_version != 2:
        raise SystemExit(f"template header_version is {header_version}, expected 2")

    old_ramdisk_off = PAGE + align(kernel_size, page_size)
    ramdisk = bytes(template[old_ramdisk_off:old_ramdisk_off + ramdisk_size])
    ramdisk_source = args.template
    if args.ramdisk:
        ramdisk = read_raw(args.ramdisk)
        ramdisk_size = len(ramdisk)
        ramdisk_source = args.ramdisk
    elif args.ramdisk_from:
        # Take the ramdisk from another ROM's boot image. The 22.2 boot image
        # cannot be the template itself: its vendor footer sits at 50.1 MiB, and
        # this kernel alone is 54.6 MiB, so nothing would fit. Keep the 24.0
        # container (footer at 57.0 MiB, DTB the 5.4 kernel was built against)
        # and carry only that ROM's ramdisk across.
        donor = load(args.ramdisk_from)
        dk, _, dr, _, _, _, _ = struct.unpack_from("<7I", donor, 8)
        dpage = struct.unpack_from("<I", donor, 36)[0]
        if donor[:8] != b"ANDROID!" or dpage != page_size:
            raise SystemExit(f"ramdisk source is not a usable boot image: {args.ramdisk_from}")
        doff = dpage + align(dk, dpage)
        ramdisk = bytes(donor[doff:doff + dr])
        ramdisk_size = dr
        ramdisk_source = args.ramdisk_from

    limit = footer_offset(template)
    if limit is None:
        raise SystemExit("template has no AVB footer; refusing to build an image the "
                         "bootloader is known to reject")

    # After the ramdisk the vendor image carries the appended device tree blob
    # (FDT magic d00dfeed, ~397 KB on vayu) up to the footer. It is not part of
    # the boot header, so nothing in mkbootimg knows about it — and zeroing it
    # costs the kernel its DT, which the bootloader answers by dropping to
    # fastboot. Carry it across verbatim.
    old_tail_off = old_ramdisk_off + align(ramdisk_size, page_size)
    tail = bytes(template[old_tail_off:limit])
    magic = tail.find(b"\xd0\x0d\xfe\xed")
    if magic < 0:
        raise SystemExit("template has no appended DTB between the ramdisk and the "
                         "footer; refusing to build an image without one")
    # Keep the DTB and nothing else. What follows it up to the vbmeta blob is
    # zero padding (397,787 B on vayu), and carrying that padding across made a
    # kernel more than a page larger than the vendor's fail the fit check below
    # even though the partition had plenty of room. The DTB's own totalsize
    # field says where it ends, so this cannot clip the blob.
    dtb_size = struct.unpack_from(">I", tail, magic + 4)[0]
    if dtb_size <= 0 or magic + dtb_size > len(tail):
        raise SystemExit(f"appended DTB claims an impossible size: {dtb_size}")
    tail = tail[:magic + dtb_size]

    new_ramdisk_off = PAGE + align(len(kernel), page_size)
    new_tail_off = new_ramdisk_off + align(ramdisk_size, page_size)
    content_end = new_tail_off + len(tail)
    if content_end > limit:
        raise SystemExit(
            f"kernel+ramdisk+dtb would end at {content_end:,}, past the vendor footer "
            f"at {limit:,}; {content_end - limit:+,} bytes over")

    # The kernel header's own image_size must fit in what the boot header
    # advertises, or the kernel is loaded truncated.
    if len(kernel) < 64 or kernel[56:60] != b"ARMd":
        raise SystemExit("kernel is not a raw arm64 Image (magic is not 'ARMd')")

    out = bytearray(template)
    # Clear the old kernel+ramdisk+dtb area so no stale payload survives a resize,
    # then lay the three pieces out again in order.
    out[PAGE:limit] = b"\0" * (limit - PAGE)
    out[PAGE:PAGE + len(kernel)] = kernel
    out[new_ramdisk_off:new_ramdisk_off + ramdisk_size] = ramdisk
    out[new_tail_off:new_tail_off + len(tail)] = tail

    struct.pack_into("<I", out, 8, len(kernel))
    struct.pack_into("<I", out, 16, ramdisk_size)
    out[576:596] = boot_id(kernel, ramdisk)

    # The footer is deliberately not recomputed: it is the vendor's, its hash no
    # longer describes the image, and the bootloader accepts exactly that.
    if out[-64:-60] != b"AVBf":
        raise SystemExit("internal error: AVB footer was not preserved")
    if b"\xd0\x0d\xfe\xed" not in out[new_tail_off:new_tail_off + len(tail)]:
        raise SystemExit("internal error: appended DTB was not written")

    with open(args.output, "wb") as f:
        f.write(out)

    print(f"template      {args.template}")
    print(f"kernel        {args.kernel} ({len(kernel):,} B, was {kernel_size:,})")
    print(f"ramdisk       {ramdisk_size:,} B at {new_ramdisk_off:,} from {ramdisk_source}")
    print(f"footer at     {limit:,} (untouched)")
    print(f"output        {args.output} ({len(out):,} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
