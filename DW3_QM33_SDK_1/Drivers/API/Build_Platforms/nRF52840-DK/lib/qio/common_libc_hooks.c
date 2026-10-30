/* 
 * SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
 * SPDX-License-Identifier: LicenseRef-QORVO-2
 */

#include <sys/stat.h>

int _lseek(int fd, int ptr, int dir)
{
    (void)fd;
    (void)ptr;
    (void)dir;
    return 0;
}

int _fstat(int fd, struct stat *st) {
    (void)fd;
    st->st_mode = S_IFCHR; // character device: read/write one byte at a time
    return 0;
}

int _isatty(int fd)
{
    (void)fd;
    return 1;
}

int _close(int fd) {
    (void)fd;
    return -1;
}
