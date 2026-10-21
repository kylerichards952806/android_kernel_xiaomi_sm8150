/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * 5.4 compatibility shim.
 *
 * Upstream split the page-table helpers out of <asm/pgtable.h> into this header
 * in 5.8. KernelSU-Next includes <linux/pgtable.h> unconditionally, so provide
 * the name here rather than patching the submodule, where the next submodule
 * update would lose the change.
 */
#ifndef _LINUX_PGTABLE_COMPAT_H
#define _LINUX_PGTABLE_COMPAT_H

#include <asm/pgtable.h>
#include <asm-generic/pgtable.h>

#endif /* _LINUX_PGTABLE_COMPAT_H */
