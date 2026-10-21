/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * 5.4 compatibility shim.
 *
 * min()/max()/clamp() lived in <linux/kernel.h> until upstream gave them their
 * own header in 5.8. KernelSU-Next includes <linux/minmax.h> directly.
 */
#ifndef _LINUX_MINMAX_COMPAT_H
#define _LINUX_MINMAX_COMPAT_H

#include <linux/kernel.h>

#endif /* _LINUX_MINMAX_COMPAT_H */
