# vayu / SM8150 5.4 port — audit

Date: 2026-10-20
Source org: <https://github.com/DUCKS-QCM-5-4> (14 repos)
Target account: <https://github.com/kylerichards952806>
Device: POCO X3 Pro, `vayu` / `M2102J20SG`, bootloader unlocked
(`ro.boot.verifiedbootstate=orange`), userdebug build, root via `adb root`.
ROM: LineageOS **24.0** = **Android 17**, API level 37
(`ro.build.version.release=17`, `ro.build.version.sdk=37`,
`ro.lineage.build.version=24.0`) — not Android 15, which is LineageOS 22.

Running kernel:

```
Linux localhost 5.4.302-qgki_aman-g61d7deab6d31 #3 SMP PREEMPT Mon Oct 19 14:08:59 CEST 2026 aarch64
Linux version 5.4.302-qgki_aman-g61d7deab6d31 (duckyduck@metonator.dev)
  (Android (15071444, +pgo, +bolt, +lto, +mlgo, based on r596125) clang version 22.0.2) #3
```

## 1. Repositories

All 14 repos are mirrored locally (`C:\k\mirrors\*.git`, bare, full history) and
pushed to `kylerichards952806` with **every branch**, not just the default one.
Two of the mirrors already existed on the account with only one branch; those now
carry all refs (`MI_RAPHAEL_5.4`, `fixes`, `backup/MI_SM8150_5.4` were missing).

| Repository | Branches |
| --- | --- |
| android_device_xiaomi_raphael | 5 |
| android_device_xiaomi_sm8150-common | 6 |
| android_device_xiaomi_vayu | 5 |
| android_hardware_qcom-caf_common | 3 |
| android_hardware_qcom_audio | 2 |
| android_hardware_qcom_display | 3 |
| android_hardware_qcom_media | 3 |
| android_kernel_qcom_sm8150 | 2 |
| android_kernel_xiaomi_sm8150 | 4 |
| kernel_techpack_camera | multiple |
| proprietary_vendor_xiaomi_raphael | multiple |
| proprietary_vendor_xiaomi_sm8150-common | 5 |
| proprietary_vendor_xiaomi_vayu | 5 |
| video-driver | 1 |

Build glue lives in a separate repo, `lineage-24.0-vayu`: local manifest, build
script, and a ROM workflow.

## 2. Device diagnostics

Collected with `adb root`:

```bash
adb root
adb shell dmesg            > dmesg.txt     # 12237 lines
adb shell zcat /proc/config.gz > config.txt # 6627 lines
adb shell getprop         > props.txt
```

Suspend/resume cycles in the capture: 5. Kernel taint: `G S W`.

### 2.1 Uninitialized ASoC runtime work — FIXED

**Symptom.** 49 occurrences of a single warning, one per suspend:

```
WARNING: CPU: 6 PID: 6187 at kernel/workqueue.c:3066 __flush_work+0x27c/0x29c
Call trace:
 __flush_work
 flush_delayed_work+0x4c/0x60
 snd_soc_suspend+0x180/0x2f8      <- sound/soc/soc-core.c
 platform_pm_suspend
 ...
 state_store
```

**Root cause.** `kernel/workqueue.c:3066` is `WARN_ON(!work->func)` — the flush
target was never initialized. The chain is:

1. `snd_soc_suspend()` calls `snd_soc_flush_all_delayed_work()`, which does
   `flush_delayed_work(&rtd->delayed_work)` for **every** runtime on the card
   (`sound/soc/soc-core.c:430-436`).
2. `rtd->delayed_work` is only initialized inside `soc_new_pcm()`
   (`sound/soc/soc-pcm.c:3364-3368`).
3. `soc_link_init()` returns as soon as a compress device is created:

   ```c
   ret = snd_soc_dai_compress_new(cpu_dai, rtd, num);
   if (ret != -ENOTSUPP) {
           if (ret < 0) dev_err(...);
           return ret;              /* <- soc_new_pcm() never runs */
   }
   ```

4. Every msm front-end link provides `.compress_new`
   (`techpack/audio/asoc/msm-dai-fe.c`, `msm_compr_new`), so those runtimes keep
   `delayed_work.work.func == NULL`.

Only the last hop differs from mainline: it is the msm compress links, not the
cirrus codec links, that take the early return.

**Impact.** Cosmetic-but-real: log spam on every suspend, kernel taint (`W`), and
a flush that silently does nothing. Not a crash, but it makes `dmesg` useless for
triaging real suspend problems and can trip CONFIG_BUG_ON_DATA_CORRUPTION style
panic-on-warn configurations.

**Fix** (`sound/soc/soc-core.c`, commit `4b4a9c0edb9f`): initialize the work at
allocation time, so the invariant holds for every runtime regardless of which
device type gets created. `soc_new_pcm()` still installs the real worker
afterwards.

```c
static void soc_pcm_runtime_noop_work(struct work_struct *work) { }

static struct snd_soc_pcm_runtime *soc_new_pcm_runtime(...)
{
        ...
        INIT_LIST_HEAD(&rtd->component_list);
        INIT_DELAYED_WORK(&rtd->delayed_work, soc_pcm_runtime_noop_work);
        ...
}
```

### 2.2 Other findings — diagnosed, not patched

| Finding | Evidence | Verdict |
| --- | --- | --- |
| `icnss` refuses suspend | `wlan_hdd_bus_suspend_noirq: suspend_noirq failed, status: -11`, `Firmware attempting wakeup, try again`, then `bus resume succeeded` | **Benign.** 1 occurrence in 5 cycles. The firmware raised an initial wakeup mid-suspend; the driver retries and recovers. Expected behaviour, not a defect. |
| `Failed to enable igmp offload` | repeated, `hdd_send_igmp_offload_params` | Informational. IGMP offload is not supported by this firmware build; the host path still works. Not worth patching. |
| `extract_gtk_rsp_event_tlv: Invalid length for GTK status` | repeated | Firmware/driver TLV length mismatch in the WLAN driver (`qcacld-3.0`). Would need a WMI parser fix; low severity, only on GTK rekey. Candidate for follow-up. |
| `PM: Device alarmtimer.0.auto failed to suspend: error -16` | 2 occurrences | Normal: a pending alarm aborted suspend. Not a bug. |
| `CPU features: SANITY CHECK: Unexpected variation in SYS_ID_ISAR4_EL1` | once, CPU4 | Harmless big.LITTLE reporting mismatch between A76 and A55 clusters. Cosmetic. |

## 3. Build verification

CI: `.github/workflows/build-kernel.yml` in `android_kernel_xiaomi_sm8150`.

Config chain (matches `BoardConfigCommon.mk` / `TARGET_KERNEL_CONFIG`):

```
vendor/sm8150-qgki_defconfig
vendor/xiaomi/sm8150-common.config
vendor/xiaomi/vayu.config
```

Verified against the live device: the generated `.config` reproduces
`CONFIG_LOCALVERSION="-qgki_aman"`, `CONFIG_ARCH_QCOM=y`, `CONFIG_RPS=y`,
`CONFIG_I2C=y` — i.e. it matches the kernel the phone is actually running.

Result: **green**. Run `39496367099` finished with `Image` (52 MB),
`kernel.config` and `SHA256SUMS.txt`; run `39501809480` then added `boot.img`
and `dtbo.img` with every step green. The artifacts were downloaded and
checked, not just assumed from a green checkmark:

```
$ grep -a -o '5\.4\.302-qgki_aman[a-z0-9-]*' Image | sort -u
5.4.302-qgki_aman-gcc903d6dda1b

$ python -c 'struct.unpack_from("<I", open("Image","rb").read(), 56)'
magic 0x644d5241        # ARMd, a valid arm64 Image header

grep CONFIG_LOCALVERSION= kernel.config
CONFIG_LOCALVERSION="-qgki_aman"
```

That is the same kernel base the phone reports
(`5.4.302-qgki_aman-g61d7deab6d31`); only the git suffix differs, as expected
for a different commit.

Four real problems were found and fixed in the workflow while getting there:

1. **`merge_config.sh` base.** Passing the fragments as positional arguments
   makes the *first* one the base (`Using ...sm8150-common.config as base`), so
   the generated `.config` contained only fragment content: `ARCH_QCOM` and
   `I2C` ended up disabled and `LOCALVERSION` was empty. Fixed by using kbuild's
   `%.config` rule, which merges onto the existing `out/.config`.
2. **Toolchain ignored.** The kernel `Makefile` has `CC = $(CROSS_COMPILE)gcc`,
   and a Makefile assignment beats an environment variable, so `CC=clang-14`
   exported in `env:` was silently ignored and the tree built with **GCC**. That
   surfaced GCC-only diagnostics (`-Wmaybe-uninitialized`,
   `-Wmisleading-indentation`) that the vendor's clang 22 never emits. Fixed by
   passing `ARCH/CC/LD/AR/NM/OBJCOPY/OBJDUMP/STRIP/READELF/CROSS_COMPILE` as
   make arguments.
3. **`llvm-nm: not found`.** The CFI/LTO link helpers shell out to unversioned
   `llvm-nm`, `llvm-objcopy` and friends instead of `$(NM)`/`$(OBJCOPY)`, so
   `MAKE_ARGS` alone was not enough. Fixed by symlinking the versioned LLVM 18
   binaries to their unversioned names.
4. **Old ld.lld.** Under clang-14 the whole tree compiled but the final vmlinux
   link failed with `relocation R_AARCH64_ABS32 cannot be used against symbol
   '__crc_*'`, because `CONFIG_MODVERSIONS` emits ABS32 references to the
   generated CRC symbols that LLVM 14's linker cannot resolve. The vendor used
   LLVM 22; CI now runs `ubuntu-24.04` with LLVM 18.

`CONFIG_CC_WERROR` stays disabled in CI because the tree is not warning-clean
in vendor code this repo does not touch (`mm/slub.c` `%zu`/`%pS`,
`kernel/sched/walt/walt.c` `%llu`, and the `-Werror` that the techpack and
qcacld `Kbuild` files add themselves). Compile errors still fail the build;
only warnings are downgraded.

## 4. Flashable images (boot.img / dtbo.img)

CI now emits `boot.img` and `dtbo.img` next to the bare `Image`. Every layout
value was read off the device instead of taken from defaults.

**vayu has no `vendor_boot` partition**, so the boot image is header **v2** with
the ramdisk inside it. Parsed from the live `boot` partition:

```
header_ver 2        page_size     4096      os_version 0x220001aa
kernel_addr 0x8000  ramdisk_addr  0x1000000 tags_addr  0x100
second_addr 0       kernel 54437904 B       ramdisk 1731322 B
```

`boot` is 128 MiB (`sde49`), `dtbo` is 32 MiB (`sde45`). The ramdisk is
legacy-LZ4, matching `BOARD_RAMDISK_USE_LZ4 := true`.

Header v2 has no DTB field, so the overlay **cannot** go inside `boot.img`. It
ships as a separate `dtbo.img` for its own partition:

```bash
fastboot flash boot boot.img
fastboot flash dtbo dtbo.img
```

Both packers are dependency-free Python (`.github/bootimg/`) and were validated
against the device rather than assumed correct:

- Repacking the device's own kernel + ramdisk reproduces its `boot.img`
  **byte-for-byte across all 56,176,640 bytes**, except the legacy 20-byte `id`
  hash (nothing validates it at boot) and 7 stale bytes of page-0 padding.
- Repacking the device's DTB reproduces its `dtbo.img` **exactly** — 291,611
  bytes identical.

A CI step (`verify_images.py`) re-parses the produced images and asserts header
v2, the exact addresses, that the embedded kernel is byte-identical to the built
`Image`, that the dtbo table is well formed, and that the result fits the 128 MiB
partition.

**Caveat:** a kernel-only build cannot generate a ROM ramdisk, so
`.github/bootimg/ramdisk-vayu.lz4` is the one extracted from the device today.
Refresh it when the ROM's ramdisk changes, or the kernel will be paired with a
stale first-stage init. The extraction command is in
`.github/bootimg/README.md`.

## 5. Constraints and blockers

- **No Linux, no local toolchain.** This machine has no `make`, `gcc`, `clang`,
  WSL2 or Docker. `VirtFirmwareEnabled = False` — virtualisation is disabled in
  firmware — so even WSL2 needs a BIOS change, an admin install and a reboot
  before it can exist. Windows cannot build AOSP (case-sensitive filesystem,
  symlinks), so CI on GitHub Actions is the build path for the kernel.
- **Disk is available, RAM is not.** `C:` has 171 GB free, but `D:` has
  **1,772 GB** free, so the ~200 GB a LineageOS 24.0 tree plus `out/` needs
  would fit on `D:`. The limit is memory: 15.8 GB RAM against 32 GB recommended
  for an Android 17 build, and 6 physical cores. A local ROM build is possible
  but slow and prone to swap thrash; `build-rom.yml` therefore still targets a
  self-hosted runner and fails fast if under 150 GB is available.
- **No LineageOS tree locally.** `repo` and `java` are not installed and cannot
  be used meaningfully from Windows. The full sync is prepared but unexecuted.
- **GitHub secondary rate limit.** Creating 15 repositories in one burst tripped
  GitHub's content-creation limit (`403 ... exceeded a secondary rate limit`).
  It cleared after roughly an hour; all repositories were created once it did.

## 6. The built kernel does not boot

`fastboot flash boot` of the CI image succeeds, but the device reboots straight
back into fastboot. Four things were measured before changing anything.

**Reference images.** The developer's finished `boot.img`/`dtbo.img` are full
partition dumps (`boot` = `0x8000000` = 128 MiB, `dtbo` = `0x2000000` = 32 MiB)
with an `avbtool 1.4.0` hash footer (`--algorithm NONE`) at the end of the
partition. Their *kernel payload is byte-identical to the stock one* (54,437,904
bytes, `5.4.302-qgki_aman-g61d7deab6d31`); only the ramdisk differs by 83 bytes.
So the reference contains no custom kernel work at all.

**Packaging is not the cause.** The CI image was rebuilt with the same full
partition size and a freshly generated `avbtool` footer with the same properties
(`com.android.build.boot.os_version`, `com.android.build.boot.fingerprint`).
Field-by-field it matches the reference; the generated vbmeta differs only in
salt/digest (both random per build) and the `avbtool` version string. Flashed,
the device still went straight to fastboot.

**AVB is not enforcing.** `/dev/block/by-name/vbmeta` was dumped with root and
parsed (`avbtool info_image`): `Algorithm: SHA256_RSA4096`, **`Flags: 3`**
(`HASHTREE_DISABLED | VERIFICATION_DISABLED`). The bootloader is not checking
the boot partition, so a missing or wrong footer cannot explain the failure.

**The kernel never runs.** `ro.boot.bootreason` is `bootloader`, `/sys/fs/pstore`
is empty and no `SYSTEM_LAST_KMSG` entry was archived, so the kernel produced no
console output at all — it dies before `console_init`, which points at the early
relocation/entry path rather than at any driver.

**Config is not the cause.** Decompressing `IKCFG_ST..IKCFG_ED` from both Images
gives 6,627 config lines that differ in exactly three entries, all toolchain
versions (`CONFIG_CC_VERSION_TEXT`, `CONFIG_CLANG_VERSION` 180103 vs 220002,
`CONFIG_AS_VERSION`) plus `CONFIG_CC_WERROR`. The arm64 header is identical too
(`image_size` 66,932,736, `flags` 0xa, magic `ARMd`, `text_offset` 0x8000).

The remaining difference is that the vendor built with Android clang 22
(`+pgo, +bolt, +lto, +mlgo`) while CI uses Ubuntu clang 18, and the parts of the
image most sensitive to the exact LLVM version are LTO, CFI and the `.rela`
relocation data used by KASLR. `build-kernel.yml` now takes `variant` and `ref`
inputs so those layers can be removed one at a time and an arbitrary commit can
be built, and the bisect is running as: `no-lto`, `no-lto-no-reloc`, and the
vendor's own commit (`kernel/vendor-baseline` = `61d7deab6d31`).

**Bisect outcome.** `no-lto` and `no-lto-no-reloc` both compiled and packaged
cleanly, and both still rebooted straight to fastboot. Removing LTO, CFI and
KASLR therefore changes nothing, which rules those out and leaves the compiler
itself.

**The toolchain is now the vendor's major version.** CI downloads the AOSP
prebuilt into the runner tool cache and fails the job unless `clang --version`
reports an Android build of 22.0.1. Two details cost time and are worth
recording: build 15071444 / r596125 from the device's config is **not
published** (the `mirror-goog-llvm-r596125-release` branch exists but has no
`clang-r596125` directory; `clang-r584948b` is the newest public LLVM 22), and
gitiles **ignores `?path=`** on `+archive`, streaming the whole repository
instead — the directory belongs in the URL
(`+archive/<sha>/<dir>.tar.gz`), whose contents land at the archive root with
no wrapper directory.

The exact build did turn out to be public, just not where the branch name
suggests: `clang-r596125` lives on the **`android17-release`** branch, whose
`AndroidVersion.txt` reads `22.0.2 / based on r596125` and which ships
`manifest_15071444.xml` — the same build number as the device's
`CONFIG_CC_VERSION_TEXT`. CI is pinned to that commit
(`29182889399818f97baa65ea238c80e8117981eb`) and asserts both the version file
and the manifest before compiling.

**The build now reproduces the vendor's configuration exactly.** Run
`39559620883` compiled `Image` (54,437,904 B) plus `boot.img` and `dtbo.img`
with that toolchain. Its `kernel.config` differs from the config extracted from
the phone in **two lines out of 5,722**, and both are the `CONFIG_CC_WERROR`
pair that CI deliberately disables — the `CONFIG_CC_VERSION_TEXT` string is
byte-identical, down to build `15071444`. The arm64 header is identical too
(`image_size` 66,932,736, `flags` 0xa, `text_offset` 0x80000), the emitted
`dtbo` payload matches the stock partition byte for byte, and `boot.img`
carries the exact device cmdline and addresses. Only 20% of the text bytes match
stock, which is expected: the tree is not the vendor's exact commit, so branch
displacements differ even though the layout and size do not.

## 5. Toolchain download: what the retry code actually did

The previous CI loop resumed with `curl --continue-at -`. That cannot work
against gitiles, and the probe proves it: requesting bytes 0-2047 of the
`clang-r596125` archive returns **`HTTP/1.1 200 OK` with `Transfer-Encoding:
chunked` and the entire stream from byte 0** — the `Range` header is ignored
because the archive is generated on demand and has no stored length. curl
therefore refuses to resume (exit 33, "does not seem to support byte ranges"),
so the four "resuming" attempts were four fresh proposals to fail. Appending the
second response onto the first would have produced a corrupt tarball.

`scripts/fetch-toolchain.sh` replaces it:

* every attempt downloads to a private temporary file, so a partial transfer is
  never mistaken for an archive;
* the archive root is checked first (`AndroidVersion.txt`, not `.gitignore`),
  then `gzip -t` for truncation, before anything is unpacked;
* `AndroidVersion.txt` and `manifest_15071444.xml` are asserted, and the tree is
  renamed into place only after both pass, so the cache never holds a half
  toolchain;
* failures are typed: **65** = wrong/corrupt content (stop, never silently
  substitute a compiler), **75** = network exhausted (the workflow may fall back
  to LLVM 18 with the artifact renamed `llvm18-fallback`, because a build that
  keeps flowing is worth more than one that dies on a CDN).

Measured on a real run, killing curl at 280,936,448 bytes: attempt 1 was
discarded, the 30 s backoff ran, attempt 2 delivered **1,090,972,094 bytes**,
passed the gzip and root checks, and reached extraction. A second test against
an unroutable URL returned **75** and left no `DEST` behind.

Caveat found during that test: unpacking on Windows (Git Bash, no symlink
privilege) fails with `Cannot create symlink` partway through. That is an
environment limitation, not a code path — the Linux runner unpacked the same
archive successfully in run `39559620883`. Extraction failures now exit 65 with
an explicit message instead of surfacing as a crash.

## 6. Comparing a ROM's toolchain against the one CI used

Shipping 2.4 GB of compiler around to answer "is this the same binary?" is
absurd, so each build now emits `toolchain-manifest.txt`: `sha256  path` for
every file, plus the `clang --version` line, `AndroidVersion.txt` and the
manifest file name. `scripts/compare-toolchain.sh <rom-dir> <manifest>` prints
version/build-id verdicts, hashes for `bin/clang`, `bin/ld.lld` and
`bin/llvm-objcopy`, and a full inventory diff with counts of identical, ROM-only
and reference-only paths. It accepts a directory as the reference too, for when
the prebuilt is unpacked locally.

Verified against a synthetic pair: identical trees report
`=> the two trees are byte-for-byte identical` with all three binaries `MATCH`;
flipping one byte reports the differing path on both sides and `DIFFER`. Two
normalisation bugs were found and fixed this way — `find .` writes `./path`
while the manifest does not, and `sha256sum` writes `*path` for binary-mode
input but `  path` for text mode, so hashes that were equal compared unequal.

## 7. Why every flashed image fell back to fastboot: it was the container, not the kernel

Measured on the device, one variable at a time (all flashes followed by a 100 s
window, `in fastboot within 32 s` = refusal, `Android up in ~24 s` = boot):

| Image flashed | Result |
|---|---|
| CI branch build, our `boot.img` (56 MB) | fastboot |
| CI branch build, padded to 128 MiB | fastboot |
| CI branch build, 128 MiB + fresh `avbtool` footer (NONE) | fastboot |
| CI **vendor-commit control** kernel, our container | fastboot |
| vendor container + CI control kernel (spliced at 0x1000) | **boots** |
| vendor container + *our* ramdisk | **boots** |
| vendor container, re-signed with our `avbtool` (NONE) | **boots** |
| our container + working image's header `id` | fastboot |
| vendor container + CI control kernel + our ramdisk, vendor footer kept | **boots** |

The kernel is not the problem. The CI-built kernel of the vendor's own commit —
same tree, same clang 22.0.2 build 15071444 — boots on the device as soon as it
is placed inside the vendor's 128 MiB `boot` partition image. What the bootloader
refuses is the container our `mkbootimg_v2.py` emits.

Header fields match the vendor image except `ramdisk_size` (ours 1,731,322 vs
1,731,405) and the `id` hash; the 128 MiB image length, page alignment and AVB
footer were each ruled out separately (padding, `--algorithm NONE` footer with a
correct hash, `id` swap all still failed). Re-signing the *vendor* image with the
same `avbtool` and no kernel change boots, so the tooling is fine — the
combination of our container and fresh footer is what is rejected.

Practical consequence: CI should stop generating a container and instead splice
the built `Image` into the vendor `boot` template (128 MiB, footer preserved),
which is the only shape that has booted on this device. Equally important, the
earlier bisect (`no-lto`, `no-lto-no-reloc`) says nothing about LTO or KASLR:
every one of those images was built with the same unbootable container, so their
`bootreason=bootloader` result was over-determined.

Side finding: `device/boot.img` and `backup/boot-now.img` are the same image, and
its kernel is `-g61d7deab6d31` built Oct 19 — the vendor tree built locally, not
a factory Xiaomi image. The factory image was overwritten earlier in this work.

## 8. The last blocker: the appended DTB

Splicing the kernel into the vendor boot image still failed — including with a
kernel that boots, which is what gave it away. The vendor image carries the
device tree blob **after the ramdisk** (FDT magic `d00dfeed` at offset
`0x3593000`, 396,837 bytes), outside anything the boot header describes. The
first splicer zeroed the whole payload area before writing the new kernel, so
every image it produced lost its DT and the bootloader fell back to fastboot —
exactly the symptom that had been blamed on the kernel for the whole session.

With the tail copied across verbatim, the *branch* kernel boots:

```
Linux version 5.4.302-vayu-kyler084-0.0.1-g8f60cc4f885a (kyler084@murena.io)
```

So the five branch patches were never the problem either. The tally of what
actually broke boot, in the order it was found:

1. a boot.img container that the bootloader rejects (fixed by splicing);
2. the splicer destroying the appended DTB (fixed by preserving the tail).

`CONFIG_LOCALVERSION_AUTO` was then turned off so the version ends at the build
number instead of a commit hash, and `KBUILD_BUILD_USER/HOST` became
`kyler084@murena.io`.

## 9. What the booted kernel's own logs say (kmsg + logcat vs the ROM's kernel)

The phone booted the branch kernel, so its dmesg (4736 lines) and logcat
(30,636 lines) were captured with `adb root`, then the same was done for a
*control*: `backup/boot-now.img`, the ROM's own `-qgki_aman-g61d7deab6d31`
kernel, flashed with `scripts/capture-control.sh` and captured on the same
userspace. Both runs finished booting (`sys.boot_completed=1`), and the 0.0.8
kernel was flashed back afterwards.

```
unique dmesg lines   stock 1807    ours 1794    shared 1725
```

The error signatures are the same line for line — 146 vs 148 i2c/GSI failures,
24 vs 24 NFC writes returning `-107`, 300 vs 306 DS28E16 battery-auth messages,
one `qcrypto` "already registered" each, 28 vs 28 audio soft-volume warnings,
4 vs 4 `reg-cooling-device` ENOMEM probes, and the same `mem-offine` typo.
`/proc/config.gz` differs from the ROM's config in three lines only:
`LOCALVERSION` (intended), `LOCALVERSION_AUTO` (intended) and `CC_WERROR` (see
below). So the kernel the bootloader now accepts behaves like the vendor's own —
it introduces no new faults, and the diagnostics below are inherited.

What those inherited faults actually are, and what was done about them:

| observation | verdict | action |
|---|---|---|
| `mem-offine node not found in FDT` (3 messages) | typo in the source, so a dmesg search for the feature misses them | fixed to `mem-offline`; confirmed in the 0.0.8 dmesg |
| `qcrypto` "already registered, aborting" | harmless duplicate `platform_driver_register`, the first registration holds `/sys/bus/platform/drivers/qcrypto` | none: the DT sets `qcom,use-sw-aes-*` on purpose, so QCE offload is intentionally off |
| 148 × `i2c_geni a84000.i2c: GSI QN err ... err:2` | `err:2` is `MSM_GPI_QUP_CH_ERROR` on the NFC bus, only during the 21–25 s firmware window; silent afterwards | none: same in the vendor kernel, NFC HAL reports `initialized=true` |
| 24 × `nfc_i2c_dev_write: failed to write -107` | HAL retries during that window, then succeeds | none |
| 306 × DS28E16 battery-auth messages, `computeS_Secret error` | `batt_verify` still reports `chip_ok=1`, ROMID reads, and stock logs the identical failure — the chip, not the driver | none |
| `Direct firmware load for modem.b* failed with error -2` ×28 | falls back to the sysfs loader and the modem comes up (`gsm.network.type=IWLAN`) | none |
| `reg-cooling-device ... regulator register err:-12` | the mm-cx cooling device never registers, so that one thermal lever is missing | none: same in stock |
| `msm_pcm_soft_volume_ctl_get ... not found` ×28 | mixer get before the PCM runtime exists; playback shows `Errors: 0` | none |
| `CONFIG_CC_WERROR` absent from the running config | CI was compiling with warnings downgraded, a workaround from when the toolchain was a guess | **fixed**: strict build is now the default (run 39595908503 compiled 3961 objects with `CC_WERROR=y` and zero warnings) |

One structural consequence worth recording: our `boot.img` keeps the *vendor's*
appended DTB verbatim, so a DT change in the source tree has no effect on what
the kernel is given. That is why the earlier `sm8150-sde.dtsi` bisect changed
nothing — the image never carried the rebuilt DTB. The DT nodes the NFC driver
complains about (`NFC VDDIO min/max`, `nfc_ldo_config`) are therefore unfixable
from the source tree while the vendor's blob is spliced in unchanged.

Artifacts: `logs/dmesg.txt`, `logs/logcat.txt` (0.0.2 on the phone),
`logs/dmesg-stock.txt`, `logs/logcat-stock.txt` (control),
`logs/dmesg-v3.txt` (0.0.8 after the fixes), `logs/ci/build.log` (strict build).

## 10. KernelSU-Next on a 5.4 vendor kernel

The kernel now carries KernelSU-Next as `drivers/kernelsu`, a submodule pinned
to **v3.4.0-legacy** (8af3d4f), wired the way the project's own
`kernel/setup.sh` does it: `obj-$(CONFIG_KSU) += kernelsu/kernel/` in
`drivers/Makefile` and `source "drivers/kernelsu/kernel/Kconfig"` in
`drivers/Kconfig`.

**Why not v3.4.2, the newest tag?** It does not compile on 5.4 at all, and the
failures are API changes, not settings:

| build | failure |
|---|---|
| 1 | `feature/sucompat.c: 'linux/pgtable.h' file not found` |
| 2 | `manager/pkg_observer.c: use of undeclared identifier 'TWA_RESUME'`, `handle_inode_event` does not refer to any field in struct fsnotify_ops` |

v3.4.0-legacy is the current release that ships `kernel/compat/kernel_compat.h`
for exactly those transitions, so it is the newest KernelSU-Next this kernel can
actually run. Its Kconfig also warns that the kprobe hook "should not be used on
kernel below 5.10", so the defconfig selects `CONFIG_KSU_SYSCALL_TABLE_HOOK`,
which patches `sys_call_table` directly.

Three things had to be added to the kernel tree itself (not to the submodule,
which any update would reset):

1. **Header shims** - 5.4 spells these headers differently; upstream split them
   out later. `include/linux/pgtable.h`, `minmax.h`, `hex.h`,
   `input-event-codes.h`, `include/crypto/sha2.h` and
   `arch/arm64/include/asm/set_memory.h` each forward to the pre-split
   definition.
2. **`include/linux/uaccess.h`** - the tree backports
   `copy_to_kernel_nofault()` from 5.8, while KernelSU still aliases it to
   `probe_kernel_write()` with a macro for kernels < 5.8. The macro rewrote the
   declaration into `long notrace probe_kernel_write((void *dst), ...)`; the
   declaration site now undefines the alias, so calls reach the real function.
3. **`fs/namespace.c` + `fs/internal.h`** - `path_umount()`/`can_umount()`.
   KernelSU's Kbuild inserts them with `sed` when `grep '^int path_umount'`
   misses, but that happens while the KSU objects compile, long after `fs/` is
   built with `-j$(nproc)`, so the first run linked with an undefined symbol.
   With the functions in the tree the insert is deterministic and KSU skips it.

**Image size.** The KSU kernel is ~131 KiB larger than the vendor's, which the
splicer rejected: "kernel+ramdisk+dtb would end at 57,102,336, past the vendor
footer at 56,971,264". The tail being copied was the 396,837-byte appended DTB
*plus* 397,787 bytes of zero padding up to the vbmeta blob. Trimming the tail at
the DTB's own `totalsize` frees that padding; a 300 KiB-larger kernel now
splices with the DTB and AVB footer intact.

**Verification so far** (run 39613607074, `0.0.17`): build green with
`CONFIG_CC_WERROR=y`, `CONFIG_KSU=y`, `CONFIG_KSU_SYSCALL_TABLE_HOOK=y`,
9 `kernelsu` strings in the Image, `boot.img` 128 MiB with one DT blob and the
AVB footer, `verify_images.py` passed, and the release published with
boot.img/dtbo.img/kernel.config/SHA256SUMS.

### The syscall-table hook cannot carry the manager

`0.0.17`–`0.0.20` built, flashed and booted, but the manager kept showing
**"Unsupported | Not integrated"** while its hooks were demonstrably live
(`sth: 5/5 syscalls hooked`, `handle_setresuid` on every uid change).

The reason is in the manager, not the kernel version: `manager/app/src/main/cpp/
ksu.cc` does not open a device or call into the kernel. It walks
`/proc/self/fd` looking for an anon-inode fd labelled `[ksu_driver]`, and every
ioctl goes through that fd. The driver installs it from
`ksu_handle_setresuid()` once `is_uid_manager()` matches, and the manager uid is
only ever learned by `track_throne()`, which is reached from `on_post_fs_data()`
— scheduled by the **execve kprobe** when zygote starts. `ksu_ksud_init()` is
`#ifdef KSU_KPROBES_HOOK` too, so the syscall-table build also skipped the init
rc injection that starts `ksud` at boot.

The table hook implements four syscall wrappers (execve, execveat, faccessat,
newfstatat) and none of the boot integration. A kernel built that way can hook
syscalls but can never bootstrap: no crowning, therefore no fd, therefore
"not integrated" forever. This is a limitation of that hook mode, not a managed
version mismatch — upgrading the manager does not help.

### Fixed by switching the hook mode (0.0.21)

The defconfig now selects `CONFIG_KSU_KPROBES_HOOK` (the upstream default).
`KPROBES`, `KRETPROBES` and `HAVE_SYSCALL_TRACEPOINTS` were already on; the table
hook had only been chosen because upstream's Kconfig warns that kprobes "should
not be used on kernel below 5.10". On this tree that warning is not a blocker —
all five kprobes register (`ksud: execve_kp: 0` … `input_event_kp: 0`,
`reboot kprobe registered successfully`).

Kernel fixes carried as patches under `.github/kernelsu/`, applied to the
submodule before each build (the submodule is upstream's, so a fix cannot live in
it): `0001-ksu-hook-reboot-syscall-table.patch` adds the reboot interception to
the table hook. It is compiled out in kprobe mode but keeps the table path
honest if that mode is ever selected again.

**Verified on hardware** (`0.0.21`, run 39630639773):

| check | result |
|---|---|
| boot | `5.4.302-vayu-kyler084-0.0.21`, `sys.boot_completed=1` |
| kprobes | `Kprobes` hook mode, all 5 probes + reboot registered |
| post-fs-data | `KernelSU: on_post_fs_data!` |
| crowning | `Crowning manager: com.rifsxd.ksunext(uid=10194)` |
| driver fd | `install fd for manager: 10194`, `ksu fd installed: 81` |
| manager UI | **Working · BUILT-IN**, `v3.4.0-legacy (33294-4)`, hook mode `Kprobes` |

### Superuser grant, verified end to end

`roottest/` is a throwaway app (one activity, no Gradle: `aapt2 link` → `javac`
against `android-34/android.jar` → `d8` → `zipalign` → `apksigner`) that runs
`/system/bin/su -c "id; echo UID=$(id -u)"` and prints what came back.

Two details worth keeping:

* Before the uid is in the allowlist, that exec fails with `ENOENT` rather than
a permission error. `ksu_handle_execve_sucompat()` bails out on
`!ksu_is_allow_uid_for_current()` before it rewrites the path, so the request
never reaches the kernel's `su` interception and the missing `/system/bin/su`
on a ROM without one is what the app sees. Granting first, then running, is the
order that works.
* Once granted, the kernel rewrites the exec to `ksud` (or `/system/bin/sh` when
`ksud` is absent) and switches credentials in flight.

Result on the device (`0.0.21`):

```
su exit 0
uid=0(root) gid=0(root) groups=0(root) context=u:r:ksu:s0
UID=0
```

The manager reports `Superusers 2` (the `adb shell` uid the operator granted by
hand, plus `com.kyler.roottest`) with hook mode `Kprobes`.

Still unverified: module mounting, which needs a metamodule installed first.
