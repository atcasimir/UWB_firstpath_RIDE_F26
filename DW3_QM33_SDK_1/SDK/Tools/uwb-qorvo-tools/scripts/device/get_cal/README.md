# get_cal

This script retrieves from the device current calibration values.

## Parameters

Arguments with expected parameter available in this script:

```{eval-rst}
+----------------+-----------------------------------------------------------------+
| Parameter      | Values                                                          |
+================+=================================================================+
| -p / --port    | Specify communication intervace                                 |
+----------------+-----------------------------------------------------------------+
| -l / --list    | list available param names and their spec                       |
+----------------+-----------------------------------------------------------------+
| -v / --verbose | prints additional debug information                             |
+----------------+-----------------------------------------------------------------+
| -f / --format  | Choose param display format.                                    |
|                |                                                                 |
|                | Available: r(repr), x(hex), b(bytes), or a(android param file). |
|                |                                                                 |
|                | Default: natural                                                |
+----------------+-----------------------------------------------------------------+
```

## Example

```
get_cal -p <port> ant_set0.tx_power_control
```
