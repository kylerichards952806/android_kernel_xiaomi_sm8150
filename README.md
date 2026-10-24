# vayu on 5.4 — my personal tweak branch

Kernel I run on my own POCO X3 Pro (vayu, M2102J20SG) on LineageOS 24.0.

Important bit first: this is **not** my port. Getting a 5.4 kernel booting on
SM8150 was Ducky's work. I picked his tree up because I wanted a couple of things
working properly on my phone, and I've been fixing and adjusting from there. Treat
anything clever in here as his, and anything broken as mine.

Ducky's tree: <https://github.com/DUCKS-QCM-5-4/android_kernel_xiaomi_sm8150>
Branch used here: `MI_SM8150_5.4`. Kernel release: `5.4.302-vayu-kyler084-0.0.x`.

## Thanks

- **Ducky** (duckyduck@metonator.dev, DUCKS-QCM-5-4) for the 5.4 SM8150 bring-up,
  the thermal work, and for keeping it public so the rest of us can even try this.
- The **KernelSU-Next** people for v3.4.0-legacy and for the 5.4 compat shims that
  make it buildable on a vendor kernel at all.
- **LineageOS** for the ROM this is built against.
- Anyone who flashes this and actually tells me what broke.

## What I changed

Most of my work has been in the battery side. The stock driver reported a battery
health screen with "Unavailable" for design and maximum capacity and a cycle count
that reset itself, plus the phone would only take plain fast charge because the
battery authentication never ran.

- **Battery stats survive reboot.** `qpnp-fg-gen4` now writes the full SDAM cookie
  instead of a partial one, so the learned capacity and cycle count aren't thrown
  away when the phone restarts. Design capacity, maximum capacity and cycle count
  now show real numbers in Settings.
- **Capacity fallback.** If the battery profile has no nominal value, the driver
  keeps the learned capacity rather than reporting zero.
- **Battery reported as verified on an aftermarket pack.** `smb5` now reads the
  DS28E16 driver's result and drops the unverified-battery charge cap once it says
  the battery is verified. My pack isn't a genuine one, so
  `CONFIG_BATT_VERIFY_FORCE_VERIFIED` (on in `vayu.config`) makes the driver answer
  `authen_result 1` / `chip_ok 1` without running the 1-Wire handshake. Turn that
  option off and the real authentication comes back.
- **Authentication result read from the right channel.** `smb5-lib` looks at
  `batt_verify` only, instead of trusting a channel that reports stale state.
- **DS28E16 binding on 5.4.** The Maxim driver binds against the platform device
  names this tree actually uses, so the node in the device tree is picked up.
- **Device tree cleanup.** Dropped the duplicated charger thermal tables in the
  vayu DTS.
- **KernelSU-Next built in.** Hooked through kprobes (the syscall-table mode can
  never bootstrap the manager), with the 5.4 header shims and `path_umount()` in
  `fs/namespace.c` that a vendor 5.4 tree needs.
- **CI does the boring parts.** Every push builds with Android clang 22, splices
  this tree's own DTB into `boot.img`, verifies the packaged images against that
  DTB, refuses to build if the branch is behind Ducky's upstream, and publishes a
  release with `boot.img`, `dtbo.img`, a TWRP zip, the exact config, checksums and
  a changelog of what changed since the previous release.
- **Notes.** `AUDIT.md` has the long version — diagnostics, the boot-image
  detective work, the KernelSU history. It's more detail than anyone needs, but
  it's there so I don't re-learn the same things twice.

## 33 W charging: I need someone with a genuine charger

The DS28E16 path is verified as far as the driver goes — authentication runs, the
result comes back verified, and the charge limit lifts. What I **cannot** verify is
a real 33 W charge, because I don't own an original Xiaomi 33 W brick. I've only
been able to watch the driver logic, not the charge rate.

So if you have the original Xiaomi 33 W charger (the MDY-11-EX one, or any genuine
33 W Xiaomi/POCO unit) and you're running this kernel, a test report would be genuinely
useful. What helps:

- Charger model, and what the phone actually does — wattage from a USB meter, or
  whether the lock screen says 33 W / shows the fast-charge animation.
- `dmesg | grep -i -E 'ds28e16|batt_verify|smb5'` from a fresh boot while plugged in.
- `cat /sys/class/power_supply/battery/current_max` and
  `cat /sys/class/power_supply/battery/voltage_now` while charging.
- Whether the battery info screen still shows capacity and cycle count after a
  couple of reboots.

There's a form for it — [open the 33 W charging test](../../issues/new?template=33w-charging-test.yml)
and paste the output in. It asks for exactly the things above, so it shouldn't take
long. Honestly, "it charges at 33 W" or "it still caps at 18 W" are both useful
answers.

## Flashing

Grab `boot.img` and the TWRP zip from [Releases](../../releases). With fastboot:

```sh
fastboot flash boot boot.img
fastboot flash dtbo dtbo.img
```

Or flash the zip in TWRP; it writes both partitions and leaves a copy of the
previous pair on `/sdcard` so you can get back.

This is built for and tested on LineageOS 24.0 only. Don't flash it on MIUI or on a
different Android version and then wonder why it doesn't boot.

Heads up that an unlocked bootloader plus a custom kernel means Play Integrity
needs help on the ROM side (PIF, Tricky Store and a keybox). That's separate from
the kernel — none of it lives in here.

## Building

Push to the branch and the GitHub Actions workflow does it: toolchain download,
build, image splice, verification, release. If you want it locally, use the same
clang the workflow pins; a random distro clang will build something, but it won't
be what the releases are.
