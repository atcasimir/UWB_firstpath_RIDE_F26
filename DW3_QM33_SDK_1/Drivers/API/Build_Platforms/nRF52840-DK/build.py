import subprocess
import fileinput
import sys
import os

EXAMPLE_SELECTION_FILE = sys.argv[1]
LOGDIR = sys.argv[2]
TEST_LIST = []
test_pass = False

def run_cmake(test_name):
    build_success = False

    cmd_cfg = f"cmake --preset=nrf52840_flash_release -DCMAKE_BUILD_EXAMPLE={test_name}"
    status_cfg = subprocess.run(cmd_cfg,
                            shell=True, check=False,
                            universal_newlines=True)
    
    if status_cfg.returncode == 0:
        cmd_build = f"cmake --build --preset nrf52840_flash_release"
        status_build = subprocess.run(cmd_build,
                                shell=True, check=False,
                                universal_newlines=True)
        
        if status_build.returncode == 0:
            build_success = True

    return build_success

original_file_content = None

# Get a list of all the lines in the file that need to be edited.
with open(EXAMPLE_SELECTION_FILE) as file:
    original_file_content = file.read()
    for line in original_file_content.split('\n'):
        #if '//#define TEST_READING_DEV_ID' in line:
        if '//#define TEST_' in line:
            TEST_LIST.append(line)

for test in TEST_LIST:
    testName = test.split()[-1]
    print("- Building " + testName)
    # Build the example
    test_pass = run_cmake(testName)
    if test_pass is False:
        print("!! Build FAILED for " + testName)
        break
    print("--> Build OK")

if test_pass is False:
    exit("At least one test failed! see logs for details... ")