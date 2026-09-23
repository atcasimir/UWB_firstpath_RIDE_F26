# set_cal

This script pushes a specific calibration value by adding the selected key and its value.

## Parameters

Arguments with expected parameter available in this script:

```{eval-rst}
+----------------+-----------------------------------------------------------------+
| Parameter      | Values                                                          |
+================+=================================================================+
| -p / --port    | Specify communication interface                                 |
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
set_cal -p <port> ant_set0.tx_power_control 3

INFO:      setting ant_set0.tx_power_control
            ant_set0.tx_power_control = Int8(3)
                                        = 3
Ok (0)
```
