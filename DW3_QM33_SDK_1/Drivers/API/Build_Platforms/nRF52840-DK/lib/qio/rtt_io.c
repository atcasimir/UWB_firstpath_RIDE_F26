/* 
 * SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
 * SPDX-License-Identifier: LicenseRef-QORVO-2
 */

#include <stdlib.h>
#include <string.h>
#include "SEGGER_RTT.h"
#include "qio.h"

#define wrstr(s) SEGGER_RTT_Write(0, s, strlen(s))

void qio_init(void) {
    SEGGER_RTT_Init();
}

_ssize_t _write(int file, const void *ptr, size_t len) {
    (void) file;  /* Not used, avoid warning */
    SEGGER_RTT_Write(0, ptr, len);
    return len;
}

_ssize_t _read(int file, char *buf, size_t nbytes)
{
    (void) file;  /* Not used, avoid warning */
    
    _ssize_t bytes_read = 0;

    while (!SEGGER_RTT_HasData(0))
    {} // block waiting for any data to appear

    bytes_read = SEGGER_RTT_Read(0, buf, nbytes);
    return bytes_read;
}



void
__assert_func(const char *file, int line, const char *function,
		   const char *reason)
{
    // printing without printf() as it might not be available
    wrstr("=====================\n");
    wrstr("Assertion failed\n");
    wrstr("Location: ");
    wrstr(file);
    (void)line; // skipping line: no standard way to print int in C
    wrstr("\nFunction: ");
    wrstr(function);
    wrstr("\nReason: ");
    wrstr(reason);
    while (1)
        ;
    // do nothing
}


