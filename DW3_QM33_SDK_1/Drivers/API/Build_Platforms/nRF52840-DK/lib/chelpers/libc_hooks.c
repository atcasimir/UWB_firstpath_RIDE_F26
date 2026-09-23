/* 
 * SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
 * SPDX-License-Identifier: LicenseRef-QORVO-2
 */

#include <stdint.h>
#include <qassert.h>
#include <sys/types.h>

extern uint32_t __heap_start__;
extern uint32_t __heap_end__;

void *
_sbrk(intptr_t count)
{
	static uint32_t current_top = (uint32_t)&__heap_start__;
	uint32_t old_top = current_top;
	QASSERT((current_top + count) < (uint32_t)&__heap_end__);
	if ((current_top + count) < (uint32_t)&__heap_end__)
		current_top += count;
	else
		return NULL;
	return (void *)old_top;
}
