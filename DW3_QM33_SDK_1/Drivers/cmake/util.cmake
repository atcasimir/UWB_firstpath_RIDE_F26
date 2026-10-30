#
# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2
#

# substitute file extension. The provided extension should contain the dot, e.g. ".bin"
function(subst_file_extension fname new_ext out_var)
    cmake_path(GET fname STEM stem)
    set(${out_var} ${stem}${new_ext} PARENT_SCOPE)
endfunction()


# add a HEX target to be generated from an ELF
function(add_hex_target elf_target hex_fname)
    add_custom_command(
        OUTPUT ${hex_fname}
        COMMAND ${CMAKE_OBJCOPY} -O ihex --gap-fill 0x00 $<TARGET_FILE:${elf_target}> $<TARGET_FILE_DIR:${elf_target}>/${hex_fname}
        DEPENDS $<TARGET_FILE:${elf_target}>
        COMMENT "Objcopying ${elf_target} to ${hex_fname}"
        )
    add_custom_target(target_${hex_fname} ALL DEPENDS ${hex_fname})
endfunction()


# add a BIN target to be generated from an ELF
function(add_bin_target elf_target bin_fname)
    add_custom_command(
        OUTPUT ${bin_fname}
        COMMAND ${CMAKE_OBJCOPY} -O binary --gap-fill 0x00 $<TARGET_FILE:${elf_target}> $<TARGET_FILE_DIR:${elf_target}>/${bin_fname}
        DEPENDS $<TARGET_FILE:${elf_target}>
        COMMENT "Objcopying ${elf_target} to ${bin_fname}"
        )
    add_custom_target(target_${bin_fname} ALL DEPENDS ${bin_fname})
endfunction()

# This functon is used by the tests to add the hex and copy it into the test folder
function(get_test_hex elf_target hex_fname destination)
    add_custom_command(
        OUTPUT ${hex_fname}
        COMMAND ${CMAKE_OBJCOPY} -O ihex --gap-fill 0x00 $<TARGET_FILE:${elf_target}> $<TARGET_FILE_DIR:${elf_target}>/${hex_fname}
        COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE_DIR:${elf_target}>/${hex_fname} ${destination}/${hex_fname}
        DEPENDS $<TARGET_FILE:${elf_target}>
        COMMENT "Objcopying ${elf_target} to ${hex_fname} and copying to ${destination}"
    )
    add_custom_target(target_${hex_fname} ALL DEPENDS ${hex_fname})
endfunction()
