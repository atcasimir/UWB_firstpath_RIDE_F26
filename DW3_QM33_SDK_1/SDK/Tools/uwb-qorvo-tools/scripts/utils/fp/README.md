# fp

Script **fp** is provided for handling conversion between natural and fixed-point numbers.

## Parameters

Arguments with expected parameter available in this script:

| Parameter      | Description                                           |
|----------------|-------------------------------------------------------|
| v              | Value to convert. May be an int, float or bytearray   |
| I              | Number of bits for the integer part                   |
| F              | Number of bits for the fractional part                |
| -r / --reverse | Convert a fix point to float instead (default: False) |
| -s / --signed  | Presence of a sign bit                                |

## Example

```
fp 28 7 1
0x38
```
