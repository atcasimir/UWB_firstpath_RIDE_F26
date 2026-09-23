# decode_uci

This script decodes command, response, and notification byte streams into a human-readable format. For more details, use `decode_uci -h`.

## Parameters

Arguments with expected parameter available in this script:

| Parameter         | Description                                      |
|-------------------|--------------------------------------------------|
| `bytes`           | Byte stream                                      |
| `-o` / `--output` | Set output file path. <br>(default: `./tmp.csv`) |

### Byte Stream Format

The byte stream should be a series of bytes in the format: 1, 2, 3, etc. Each byte can be separated by:
- No separator
- A space (` `)
- A dot (`.`)
- A colon (`:`)

**Note:** If using a space (` `) as the separator, the entire byte stream must be enclosed in single quotes (`' '`).

## Example

Examples:

```
decode_uci 20.02.00.00
decode_uci '20 02 00 00'
decode_uci 410300020000 41.00.00.01.00  61.02.00.06.2a.00.00.00.00.00
decode_uci 410300020000 41.00.00.01.00  61.02.00.06.2a.00.00.00.00.00 -o ./output_file.csv
```
