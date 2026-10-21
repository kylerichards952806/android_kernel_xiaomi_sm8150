#!/usr/bin/env python3
"""Build a TWRP-flashable zip from the packaged kernel release files.

The zip writes boot.img and dtbo.img straight to their by-name partitions, so
it behaves the same whatever ROM is installed. It is byte-for-byte reproducible
from the same inputs: fixed timestamps and ordering, no compression on the
images (they are already dense), deflate on the small text files.
"""
import argparse
import pathlib
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
FIXED_TIME = (1980, 1, 1, 0, 0, 0)  # zip's epoch, keeps output reproducible


def add(zf, name, data, mode=0o644):
    info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
    info.external_attr = (0o100000 | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", required=True, help="directory with boot.img/dtbo.img")
    ap.add_argument("--version", required=True, help="kernel version, e.g. 5.4.302-vayu-kyler084-0.0.19")
    ap.add_argument("--out", required=True, help="zip to write")
    args = ap.parse_args()

    dist = pathlib.Path(args.dist)
    boot = dist / "boot.img"
    dtbo = dist / "dtbo.img"
    for path in (boot, dtbo):
        if not path.is_file():
            raise SystemExit(f"missing {path}")

    updater = (HERE / "update-binary").read_text().replace("@VERSION@", args.version)
    readme = (
        "vayu kernel %s\n"
        "\n"
        "TWRP: Install -> select this zip. It writes boot.img and dtbo.img and\n"
        "saves the previous pair to /sdcard/vayu-kernel-backup-%s/ first.\n"
        "Fastboot equivalent:\n"
        "  fastboot flash boot boot.img\n"
        "  fastboot flash dtbo dtbo.img\n"
        % (args.version, args.version)
    )

    out = pathlib.Path(args.out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        add(zf, "META-INF/com/google/android/update-binary", updater, 0o755)
        add(zf, "META-INF/com/google/android/updater-script", "# vayu kernel installer\n")
        add(zf, "README.txt", readme)
        # Images are deflated: three quarters of a 128 MiB boot partition is
        # zero padding, so this cuts the download roughly in half, and TWRP
        # refuses entries it cannot unpack anyway.
        for path in (boot, dtbo):
            info = zipfile.ZipInfo(path.name, date_time=FIXED_TIME)
            info.external_attr = (0o100000 | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(path, "rb") as src, zf.open(info, "w") as dst:
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    dst.write(chunk)

    print(f"wrote {out} ({out.stat().st_size:,} B) for {args.version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
