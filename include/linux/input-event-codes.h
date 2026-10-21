/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * 5.4 compatibility shim.
 *
 * The KEY_*/BTN_*/EV_* constants live in <uapi/linux/input-event-codes.h> here
 * and only got a kernel-internal alias in 5.11. KernelSU-Next includes the
 * generic name to read the power key.
 */
#ifndef _LINUX_INPUT_EVENT_CODES_COMPAT_H
#define _LINUX_INPUT_EVENT_CODES_COMPAT_H

#include <uapi/linux/input-event-codes.h>

#endif /* _LINUX_INPUT_EVENT_CODES_COMPAT_H */
