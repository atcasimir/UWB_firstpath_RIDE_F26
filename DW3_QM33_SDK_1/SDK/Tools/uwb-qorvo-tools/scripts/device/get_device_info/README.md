# get_device_info

This script displays information about the device based on information retrieved from the `CORE_GET_DEVICE_INFO_RSP`.

## Parameters

Arguments with expected parameter available in this script:

| Parameter      | Values                              |
|----------------|-------------------------------------|
| -p / --port    | Specify communication interface     |
| -v / --verbose | prints additional debug information |

## Response Fields

Below are the details of each field in the response:

| Field                    | Length  | Description                                                        |
|--------------------------|---------|--------------------------------------------------------------------|
| Status                   | 1 Octet | Indicates the status of the response.                              |
| UCI Version              | 2 Octets| Supported UCI version.                                             |
| MAC Version              | 2 Octets| Suppoted MAC version.                                              |
| PHY Version              | 2 Octets| Suppoted PHY version.                                              |
| UCI Extension Version    | 2 Octets| Suppoted UCI Extension version.                                    |
| Vendor Specific Info Len | 1 Octet | The length of the vendor-specific information.                     |
| Vendor Specific Info     | n Octets| Vendor-specific information such as chip version and chip variant. |

> **Note:** For more details refer to ``CORE_GET_DEVICE_INFO_RSP`` in ``FIRA UCI Technical Specification``.

### Vendor Specific Info Fields

These fields contain vendor-specific information such as chip version and chip variant.

| Field                    | Description                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| QMF Version              | Qorvo Mobile Firmware (QMF) version.                                        |
| OEM Version              | Original equipment manufacturer (OEM) version, possible to set by customer. |
| Build Job                | Information about the build job.                                            |
| SOC ID                   | System on Chip (SOC) identifier.                                            |
| Device ID                | Device identifier.                                                          |
| Packaging ID             | Packaging type: 'sip' (System in Package) or 'soc' (System on Chip).        |

> **Note:** The fields `packaging id` and `build job` are optional and may not be present for each firmware or device.

## Example

```
get_device_info -p <port>

Pinging device at COM18:
# Get Device Info:
    status:              Ok (0x0)

[...]
```
