/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * 5.4 compatibility shim.
 *
 * Upstream merged <crypto/sha256.h> and <crypto/sha512.h> into this header in
 * 5.9. KernelSU-Next includes <crypto/sha2.h> and then <crypto/sha.h> for the
 * SHA-2 constants.
 */
#ifndef _CRYPTO_SHA2_COMPAT_H
#define _CRYPTO_SHA2_COMPAT_H

#include <crypto/sha256.h>
#include <crypto/sha512.h>

#endif /* _CRYPTO_SHA2_COMPAT_H */
