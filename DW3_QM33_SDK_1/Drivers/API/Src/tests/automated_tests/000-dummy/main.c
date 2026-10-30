/*
 * @copyright SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
 *            SPDX-License-Identifier: LicenseRef-QORVO-2
 */

 #include "dummy.h"
 #include <stdio.h>

 int main(void)
 {
     bool test_result = test_dummy();
 
     if (test_result == false)
     {
        printf("--- FAIL ---\n");
     }
     else
     {
        printf("--- PASS ---\n");
     }
 
     return 0;
 }