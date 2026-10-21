#!/usr/bin/env python3
"""Pick the built DTB that belongs in the boot image.

The boot image carries an appended device tree, and the bootloader uses it as
the base the dtbo overlays are applied to. The vendor template ships one
specific base (vayu's is the SM8150 **v2** one), and a kernel tree builds
several (`sm8150-xiaomi.dtb`, `sm8150-v2-xiaomi.dtb`). Splicing the wrong one
means the overlay is applied to a tree describing different silicon, so the
choice is made from the identifiers the bootloader itself matches on:
`qcom,msm-id` and `qcom,board-id` at the root of the FDT.

    pick_dtb.py --template boot-template.img.gz \
        out/arch/arm64/boot/dts/xiaomi/sm8150-xiaomi.dtb \
        out/arch/arm64/boot/dts/xiaomi/sm8150-v2-xiaomi.dtb
    -> path of the best match on stdout, mismatch table on stderr
"""

import argparse
import gzip
import struct
import sys

FDT_MAGIC = b"\xd0\x0d\xfe\xed"


def load(path):
    with open(path, "rb") as f:
        head = f.read(2)
    if head == b"\x1f\x8b":
        with gzip.open(path, "rb") as f:
            return f.read()
    with open(path, "rb") as f:
        return f.read()


def find_fdt(blob):
    """First FDT in a blob: a bare .dtb, or the appended tail of a boot image."""
    off = blob.find(FDT_MAGIC)
    if off < 0:
        return None
    size = struct.unpack_from(">I", blob, off + 4)[0]
    if size <= 0 or off + size > len(blob):
        return None
    return blob[off:off + size]


def root_props(fdt):
    """(name -> raw value) for the root node only."""
    (magic, _total, off_struct, off_strings, _off_rsv, _version, _last,
     _cpuid, size_strings, size_struct) = struct.unpack_from(">10I", fdt, 0)
    if magic != 0xD00DFEED:
        raise SystemExit("not an FDT")
    strings = fdt[off_strings:off_strings + size_strings]
    block = fdt[off_struct:off_struct + size_struct]

    pos, depth, props = 0, 0, {}
    while pos + 4 <= len(block):
        tok = struct.unpack_from(">I", block, pos)[0]
        pos += 4
        if tok == 1:          # FDT_BEGIN_NODE
            depth += 1
            end = block.index(b"\0", pos)
            pos += (end - pos + 1 + 3) & ~3
        elif tok == 2:        # FDT_END_NODE
            depth -= 1
        elif tok == 3:        # FDT_PROP
            length, name_off = struct.unpack_from(">II", block, pos)
            pos += 8
            name = strings[name_off:strings.index(b"\0", name_off)].decode()
            value = block[pos:pos + length]
            pos += (length + 3) & ~3
            if depth == 1:
                props[name] = value
        elif tok == 4:        # FDT_NOP
            continue
        elif tok == 9:        # FDT_END
            break
        else:
            raise SystemExit("corrupt FDT structure block")
    return props


def cells(value, label):
    if len(value) % 4:
        raise SystemExit(f"{label} is not a list of 32-bit cells")
    return struct.unpack(">%dI" % (len(value) // 4), value)


def describe(fdt):
    p = root_props(fdt)
    out = {}
    for key in ("qcom,msm-id", "qcom,board-id"):
        if key in p:
            out[key] = cells(p[key], key)
    for key in ("model", "qcom,msm-name"):
        if key in p:
            out[key] = p[key].rstrip(b"\0").decode("latin1")
    return out


def matches(template, candidate):
    """True when every (msm-id, board-id) pair of the candidate is in the base."""
    t_ids = set(template.get("qcom,msm-id", ()))
    t_boards = set(template.get("qcom,board-id", ()))
    c_ids = set(candidate.get("qcom,msm-id", ()))
    c_boards = set(candidate.get("qcom,board-id", ()))
    return bool(c_ids) and c_ids <= t_ids and (not t_boards or c_boards <= t_boards)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True,
                    help="boot image (or .dtb) whose appended FDT is the reference")
    ap.add_argument("candidates", nargs="+", help="built .dtb files to choose from")
    args = ap.parse_args()

    template_blob = load(args.template)
    template_fdt = find_fdt(template_blob)
    if template_fdt is None:
        raise SystemExit(f"{args.template}: no FDT found")
    template = describe(template_fdt)
    print(f"template: {template}", file=sys.stderr)

    scored = []
    for path in args.candidates:
        try:
            blob = load(path)
        except OSError as exc:
            print(f"  skip {path}: {exc}", file=sys.stderr)
            continue
        fdt = find_fdt(blob)
        if fdt is None:
            print(f"  skip {path}: no FDT", file=sys.stderr)
            continue
        info = describe(fdt)
        ok = matches(template, info)
        scored.append((ok, len(fdt), path, info))
        print(f"  {'match  ' if ok else 'mismatch'} {path}: {info}", file=sys.stderr)

    winners = [s for s in scored if s[0]]
    if not winners:
        print("no built DTB matches the template's msm-id/board-id; refusing to "
              "splice a device tree for different silicon", file=sys.stderr)
        return 1

    # Several bases can be valid for one msm-id (vayu's overlay lists both); keep
    # the tree the template itself came from by preferring the same model name.
    model = template.get("model", "")
    winners.sort(key=lambda s: (s[3].get("model", "") != model, -s[1]))
    print(winners[0][2])
    return 0


if __name__ == "__main__":
    sys.exit(main())
