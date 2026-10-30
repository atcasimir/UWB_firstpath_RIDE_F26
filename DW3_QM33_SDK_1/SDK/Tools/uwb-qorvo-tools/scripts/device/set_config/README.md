# set_config

This script sets a configuration parameter value; it can be used to activate firmware debug traces.

## Parameters

Arguments with expected parameter available in this script:

| Parameter      | Values                                    |
|----------------|-------------------------------------------|
| -p / --port    | Specify communication interface           |
| -l / --list    | list available param names and their spec |
| -v / --verbose | prints additional debug information       |

## Example

```
set_config ChannelNumber 5 -p <port>
OK (0)
```
