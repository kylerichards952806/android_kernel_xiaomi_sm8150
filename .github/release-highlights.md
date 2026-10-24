<!--
Hand-written highlights for the release notes. The workflow drops this file in
above the commit list, so what is written here appears at the top of every
release until it is changed. Update or empty it when the next build has
something different to say.
-->

### What's in this build

Two battery problems that have been there since this tree was ported to 5.4, both
fixed in the kernel rather than worked around in userspace.

The first was the battery stats screen. It showed "Unavailable" for design and
maximum capacity, and the cycle count went back to a fresh number after every
reboot. The fuel gauge was writing a partial SDAM cookie, so the learned capacity
never survived a restart. It now writes the whole cookie, and falls back to the
learned capacity when the battery profile has no nominal value instead of
reporting zero. Design capacity, maximum capacity and cycle count show real
numbers now, and they stay put across reboots.

The second was fast charging. The pack has a Maxim DS28E16 authentication chip and
the driver had been sitting in the tree unused, so nothing ever asked the battery
who it was. SMB5 now reads the result five seconds after probe, retries while the
supplier is still coming up, and re-checks every minute so a replaced battery gets
judged on its own merit.

My pack is an aftermarket one, and a genuine handshake with it is not something I
can rely on, so this build sets `CONFIG_BATT_VERIFY_FORCE_VERIFIED`: the driver
still registers `batt_verify` and answers the charger, but reports
`authen_result 1` / `chip_ok 1` without touching the 1-Wire bus. The unverified
charge cap is dropped, which is the whole point. If you run a genuine pack and
want the real check back, turn that option off and the handshake returns.

What I cannot tell you is whether it actually charges at 33 W, because I don't own
a genuine Xiaomi 33 W charger. That is as far as the driver side goes on my own.

So if you have the original 33 W brick, please fill in the
[33 W charging test](https://github.com/kylerichards952806/android_kernel_xiaomi_sm8150/issues/new?template=33w-charging-test.yml)
form: charger model, measured wattage, the dmesg authentication lines, the sysfs
charging values and the battery info screen. "Still caps at 18 W" is just as
useful to hear as "it does 33 W".

All of this is built on Ducky's 5.4 SM8150 port. The base is his work; the fixes
above are mine on top of it.
