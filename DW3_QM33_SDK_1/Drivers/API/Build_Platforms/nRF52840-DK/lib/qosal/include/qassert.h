/* 
 * SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
 * SPDX-License-Identifier: LicenseRef-QORVO-2
 */

#ifndef QASSERT_HEADER_H
#define QASSERT_HEADER_H

/* if QOSAL is not present replace QASSERT by assert. */
#include <assert.h>
#define QASSERT(x) assert(x)

#endif /* QASSERT_HEADER_H */
