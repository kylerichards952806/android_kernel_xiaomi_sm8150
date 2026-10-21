/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * 5.4 compatibility shim.
 *
 * hex_asc/hex_to_bin/hex2bin/bin2hex are declared in <linux/kernel.h> here;
 * upstream moved them to this header in 5.9. KernelSU-Next includes it directly.
 */
#ifndef _LINUX_HEX_COMPAT_H
#define _LINUX_HEX_COMPAT_H

#include <linux/kernel.h>

#endif /* _LINUX_HEX_COMPAT_H */
