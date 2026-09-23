/* 
 * SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
 * SPDX-License-Identifier: LicenseRef-QORVO-2
 */
#ifndef QIO_H
#define QIO_H


/*! This function should be called early in the program to initialise the 
 * standard input-output subsystem, before calling to any of the stdio functions 
 * like printf() or scanf()
 */
void qio_init(void);

#endif // QIO_H
