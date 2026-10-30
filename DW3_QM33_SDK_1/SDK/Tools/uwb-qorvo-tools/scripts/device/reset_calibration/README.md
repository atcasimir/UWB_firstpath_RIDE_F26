# reset_calibration

This script resets the DUT's calibration parameters to their default values.

## Parameters

Arguments with expected parameter available in this script:

| Parameter      | Values                                  |
|----------------|-----------------------------------------|
| -p / --port    | Specify communication interface         |
| -v / --verbose | prints additional debug information     |
| --timeout      | time in second until the script timeout |

## Example

```
reset_calibration -p <port> --timeout 6
```
