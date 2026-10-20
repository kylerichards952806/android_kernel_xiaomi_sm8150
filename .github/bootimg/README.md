# boot image tooling for vayu

`mkbootimg_v2.py` and `mkdtimg.py` are small, dependency-free packers used by
`../workflows/build-kernel.yml` so producing a flashable image needs nothing
beyond `python3`.

Both were validated against the device itself rather than assumed correct:

| Tool | Validation |
| --- | --- |
| `mkbootimg_v2.py` | Repacking the live `boot` partition's own kernel + ramdisk reproduces the vendor image byte-for-byte across all 56,176,640 bytes, apart from the legacy 20-byte `id` hash (nothing validates it) and 7 stale bytes of page-0 padding. |
| `mkdtimg.py` | Repacking the live `dtbo` partition's DTB reproduces it **exactly** — 291,611 bytes, byte-identical. |

## vayu boot image facts (read from the device)

vayu has **no `vendor_boot` partition**, so it uses a header **v2** boot image
with the ramdisk inside `boot`:

```
header_version 2      page_size      4096
kernel_addr    0x8000 ramdisk_addr   0x1000000
tags_addr      0x100  second_addr    0
os_version     0x220001aa
cmdline        androidboot.hardware=qcom androidboot.console=ttyMSM0 ...
```

`boot` is 128 MiB (`sde49`); `dtbo` is 32 MiB (`sde45`).

Because header v2 has no DTB field, the device tree overlay cannot live inside
`boot.img`. It ships as a separate `dtbo.img` for the `dtbo` partition:

```bash
fastboot flash boot  boot.img
fastboot flash dtbo  dtbo.img
```

## `ramdisk-vayu.lz4`

This is the ramdisk extracted from the device's own `boot` partition
(`/dev/block/by-name/boot`, 2026-10-20). It is legacy-LZ4 compressed, matching
`BOARD_RAMDISK_USE_LZ4 := true`.

A kernel-only build has no way to generate a ROM's ramdisk, so this one is
reused verbatim. **Refresh it whenever the installed ROM's ramdisk changes**,
otherwise a kernel from CI will be paired with a stale first-stage init:

```bash
adb root
adb shell dd if=/dev/block/by-name/boot of=/data/local/tmp/boot.img bs=1M
adb pull /data/local/tmp/boot.img
python3 - <<'PY'
import struct
d = open('boot.img', 'rb').read()
ks, ka, rs = struct.unpack_from('<3I', d, 8)
page = struct.unpack_from('<I', d, 0x24)[0]
off = page + ((ks + page - 1)//page)*page
open('ramdisk-vayu.lz4', 'wb').write(d[off:off+rs])
PY
```
