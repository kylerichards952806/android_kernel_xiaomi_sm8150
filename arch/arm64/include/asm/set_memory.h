/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * 5.4 compatibility shim.
 *
 * arm64 implements set_memory_ro/rw/x/nx in arch/arm64/mm/pageattr.c but has no
 * <asm/set_memory.h> of its own until much later; <asm-generic/set_memory.h>
 * carries the prototypes. KernelSU-Next includes <asm/set_memory.h> directly.
 */
#ifndef __ASM_SET_MEMORY_COMPAT_H
#define __ASM_SET_MEMORY_COMPAT_H

#include <asm-generic/set_memory.h>

#endif /* __ASM_SET_MEMORY_COMPAT_H */
