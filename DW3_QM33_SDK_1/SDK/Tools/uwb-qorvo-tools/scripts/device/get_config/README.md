# get_config

This script retrieves the device configuration; it can be used to display
firmware debug traces configuration.

## Parameters

Arguments with expected parameter available in this script:

| Parameter       | Values                                           |
|-----------------|--------------------------------------------------|
| -p / --port     | Specify communication interface                  |
| -l / --list     | list available param names and their spec        |
| -v / --verbose  | prints additional debug information              |
| -b / --as-bytes | show the key value as a byte stream              |
| -x / --as-hex   | show the key value in hex format                 |
| -r / --as-repr  | show the key value in format used to set it back |

## Example

```
get_config -p <port>
State                = DeviceState.Ready

[...]
```
