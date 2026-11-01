# High-Frequency Anemometer Data Acquisition

## Overview

This example demonstrates how to implement a custom, high-frequency data acquisition and transmission application.

### Requirements

The application requires continuous wind speed and direction measurements from a Barani MeteoWind2 anemometer at a frequency of **10 Hz (10 measurements per second)**. The instrument is connected to the datalogger via Modbus. Each wind measurement must be sent in a UDP message over the Ethernet interface to a local server. The application also requires periodic synchronization of the datalogger's internal clock with an NTP server. It is imperative to maintain an exact 100 ms measurement interval and avoid the accumulation of timing delays.

### Implementation

Due to the continuous measurement requirement and the use of a proprietary UDP protocol, the simplest approach was to completely override the datalogger's default functionality using a single script, rather than relying on the standard built-in SmartObserverPlus functionality and lifecycle hooks.

The script:

1. Enables the datalogger's watchdog timer.
2. Activates the power supply to the anemometer.
3. Configures an RS-485 interface for Modbus RTU communication.
4. Reads wind speed and direction from two Modbus input registers.
5. Converts the raw register values into engineering units.
6. Encodes each measurement into a proprietary UDP message format with a checksum and sequence counter.
7. Sends the message over Ethernet to a configured local server.
8. Controls the execution timing to target a measurement interval of 100 milliseconds.
9. Supports periodic clock synchronization using SNTP.
10. Continuously resets the watchdog timer to prevent an unintended system restart.

## Hardware Setup

- Geolux SmartObserverPlus datalogger
- Barani MeteoWind2 anemometer with Modbus RTU interface, connected to the first RS-485 channel and the first power output of the datalogger
- Ethernet connection to the receiving server

### Modbus Configuration

| Parameter | Value |
|---|---|
| Interface | RS485_1 |
| Baud rate | 19200 |
| Parity | None |
| Data bits | 8 |
| Stop bits | 1 |
| Modbus slave address | 1 |
| Function | Read Input Registers |
| Starting register | 6 |
| Register count | 2 |

The first returned register contains wind speed, and the second contains wind direction.

Both values are divided by 100 to convert them into engineering units, according to the manufacturer's specifications.

## Network Configuration

The following parameters are defined at the beginning of the script:

```python
server = "10.10.10.5"
port = 8080
sntp_server = "pool.ntp.org:123"
do_sync_time = False
```

- `server`: IP address of the receiving UDP server.
- `port`: Destination UDP port.
- `sntp_server`: NTP server used for clock synchronization.
- `do_sync_time`: Enables or disables periodic clock synchronization.

**Note:** NTP synchronization is disabled in the supplied script (`do_sync_time = False`). Set it to `True` to enable periodic synchronization. The implementation uses the configured Ethernet interface for SNTP requests.

## UDP Message Format

Each successful measurement is formatted into a proprietary ASCII message.

The payload has the following structure:

```text
$<checksum>,<sequence>,8,1,<wind_speed>,<wind_direction>#
```

Where:

- `checksum`: Sum of ASCII character values of the payload before the checksum prefix.
- `sequence`: Incrementing message counter.
- `8,1`: Fixed fields used by the proprietary receiving protocol.
- `wind_speed`: Measured wind speed.
- `wind_direction`: Measured wind direction.
- `#`: Message terminator.

The message is transmitted using the SmartObserverPlus UDP API:

```python
udp.send(logger.NETIF_ETHERNET, server, port, message)
```

UDP is connectionless and does not provide delivery acknowledgment. The script does not implement retransmission or buffering of failed packets.

## Measurement Timing

The script targets a fixed **100 ms measurement period**, corresponding to 10 Hz.

At the beginning of each cycle, it records the internal tick count:

```python
cycle_start_time = logger.get_tick_count()
```

After acquiring and transmitting the measurement, it calculates how much time remains in the current 100 ms period and delays execution accordingly.

The script also includes a basic compensation mechanism for cycles that exceed the intended duration.

**Timing limitation:** The script targets 10 Hz but does not guarantee exactly 10 measurements per second under all operating conditions. Blocking Modbus reads, network operations, and other processing delays can introduce timing deviations.

## Time Synchronization

The script demonstrates how to synchronize the datalogger's internal real-time clock using SNTP:

```python
server_timestamp = sntp_client.get_timestamp(
    logger.NETIF_ETHERNET,
    sntp_server
)

if server_timestamp > 0:
    logger.set_time_utc(server_timestamp)
```

When enabled, the synchronization function is called after every 10,000 acquisition-loop iterations, corresponding to approximately 1,000 seconds (16 minutes and 40 seconds) at the nominal 10 Hz rate.

The synchronization interval therefore depends on the actual execution frequency.

## SmartObserverPlus Python APIs Demonstrated

| Module | Function | Purpose |
|---|---|---|
| `output_power` | `set()` | Enable anemometer power |
| `serial` | `configure()` | Configure the RS-485 interface |
| `modbus` | `read_input_registers()` | Read wind speed and direction |
| `udp` | `send()` | Transmit measurements via Ethernet |
| `sntp_client` | `get_timestamp()` | Retrieve network time |
| `logger` | `set_time_utc()` | Update the datalogger clock |
| `logger` | `get_tick_count()` | Implement acquisition timing |
| `logger` | `delay_ms()` | Delay execution |
| `logger` | `watchdog_enable()` | Enable watchdog protection |
| `logger` | `watchdog_reset()` | Keep the watchdog alive |

## Important Notes

- The script is intended for applications where measurement frequency and direct control of communication are more important than the standard datalogger workflow.
- Network time synchronization is optional and disabled in the supplied example.
- The script's exception handler prints a diagnostic message and exits the acquisition loop; it does not implement automatic recovery within the Python application.