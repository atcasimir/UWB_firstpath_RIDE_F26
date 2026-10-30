# get_cap

This script retrieves DUT's (Device Under Test) capabilities through FiRa UCI commands CORE_GET_CAPS_INFO_CMD/CORE_GET_CAPS_INFO_RSP.

## Parameters

Arguments with expected parameter available in this script:

| Parameter      | Values                              |
|----------------|-------------------------------------|
| -p / --port    | Specify communication interface     |
| -v / --verbose | prints additional debug information |

## Example

```
get_cap -p <port>

# Get Device Capability Parameter

# Get Caps Info:
        status:              Ok (0x0)
        Caps:

[...]
```
