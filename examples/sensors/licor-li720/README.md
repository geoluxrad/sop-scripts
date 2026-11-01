# High-Frequency LI-COR Data Acquisition

## Overview

This example demonstrates how to implement continuous, high-frequency serial data acquisition and JSON message parsing from a LI-COR LI-720 carbon node / evapotranspiration instrument using the Geolux SmartObserverPlus datalogger.

### Requirements

The application requires continuous reception of measurement data from a LI-COR LI-720 device at a nominal frequency of **10 Hz (10 measurements per second)**.

The instrument is connected to the datalogger via an RS-232 interface and continuously transmits measurement data in JSON format.

Unlike a typical sensor interface, where the datalogger periodically requests individual measurements, the LI-COR device streams data continuously. The script must receive and process incoming serial data without losing measurements or corrupting messages when the serial read operation returns incomplete data.

Each JSON message contains an array of measurement values, which must be mapped to their corresponding variable names for further processing.

### Implementation

Due to the continuous high-frequency data stream, the application uses a standalone Python script with its own execution loop rather than the standard SmartObserverPlus measurement lifecycle hooks.

The script:

1. Configures the RS-232 interface for communication with the LI-COR device.
2. Continuously reads incoming serial data in chunks of up to 512 bytes.
3. Maintains a persistent receive buffer to handle JSON messages split across multiple serial reads.
4. Identifies complete messages using end-of-line delimiters (`\r`, `\n`, or `\r\n`).
5. Validates the basic structure of each message and parses it as JSON.
6. Extracts the measurement array from the `data` field.
7. Maps the received measurement values to predefined variable names.
8. Extracts the `crc32` field included in the received message.
9. Prints selected measurement values for debugging and verification.
10. Repeats the process continuously to handle the incoming data stream.

The example illustrates how to implement continuous serial data reception, buffering, and structured message parsing independently of the standard datalogger acquisition workflow.

## Hardware Setup

- Geolux SmartObserverPlus datalogger
- LI-COR LI-720 device with serial JSON data output over RS-232 line connected to the second RS-232 channel on the datalogger

### Serial Configuration

The script configures the serial interface using the following parameters:

| Parameter | Value |
|---|---|
| Interface | RS232_2 |
| Baud rate | 115200 |
| Parity | None |
| Data bits | 8 |
| Stop bits | 1 |
| Data format | JSON |
| Message delimiter | CR, LF, or CRLF |
| Nominal data frequency | 10 Hz |

The interface is initialized using:

```python
PORT = serial.RS232_2
serial.configure(
    PORT,
    115200,
    serial.PARITY_NONE,
    serial.DATA_EIGHT,
    serial.STOP_ONE
)
```

## Serial Data Reception

The script continuously reads incoming data from the RS-232 interface:

```python
chunk = serial.read(PORT, 512, 150)
```

The arguments specify:

- `PORT`: Serial interface used for communication.
- `512`: Maximum number of bytes to read.
- `150`: Read timeout in milliseconds.

Because serial communication provides a continuous stream of bytes, individual read operations do not necessarily correspond to complete JSON messages.

A single serial read may contain a partial message, one complete message, or multiple messages.

### Receive Buffer

To handle this, the script maintains a persistent receive buffer:

```python
remainder = bytearray()
```

Each received chunk is appended to this buffer:

```python
remainder.extend(chunk)
```

The `parse_json_lines()` function searches the buffer for complete newline-delimited messages.

Complete messages are extracted and parsed, while any incomplete data at the end of the buffer is retained for the next read operation.

This approach ensures that JSON messages split across multiple serial reads can be reconstructed correctly.

### JSON Message Parsing

Each complete line is checked to determine whether it contains a valid JSON object.

The script:

1. Removes leading and trailing whitespace from the candidate message.
2. Checks whether the message starts with `{` and ends with `}`.
3. Decodes the message using UTF-8.
4. Parses the JSON using `json.loads()`.
5. Returns the parsed object if it is a dictionary.

Invalid or incomplete JSON messages are ignored.

The implementation supports different line-ending conventions, including carriage return, line feed, and carriage return followed by line feed.

## Measurement Data Mapping

The received JSON messages contain a `data` field holding the measurement values.

The script defines a list of variable names corresponding to their positions in the measurement array:

```python
VAR_NAMES = [
    "IDX", "U", "V", "W", "T_SONIC", "T_SONICH",
    "SOS", "TA", "RH", "PA",
    "V_r0", "V_w0", "V_c0", "V_ref",
    "V_h2o", "V_co2", "V_par", "V_det",
    "T_det", "T_src", "RH_src", "VTX",
    "PITCH", "ROLL", "HEADING", "Status",
    "SEQ", "VIN", "RSSI", "PPFD",
    "H2O_ABS", "CO2_ABS", "H2O", "CO2",
    "CO2_MOLAR_DENSITY", "H2O_MOLAR_DENSITY"
]
```

The `_map_vars()` function converts the received values into a dictionary indexed by variable name.

The function supports measurement data represented as an ordered array or a dictionary.

For example, an array containing the first four values is mapped to:

```python
{
    "IDX": 100,
    "U": 1.25,
    "V": 0.42,
    "W": -0.08
}
```

The names and their ordering must match the data format configured on the LI-COR device.

### Example Output

The script extracts and prints a subset of the available measurement variables:

- `IDX`: Measurement index
- `U`, `V`, `W`: Wind velocity components
- `TA`: Air temperature
- `RH`: Relative humidity
- `PA`: Atmospheric pressure
- `crc32`: CRC field from the received JSON message

The output is printed as a Python dictionary, for example:

```python
{
    "IDX": 100,
    "U": 1.25,
    "V": 0.42,
    "W": -0.08,
    "TA": 23.5,
    "RH": 56.2,
    "PA": 101.3,
    "crc32": 1234567890
}
```

The values above are illustrative and do not represent actual measurements.

## High-Frequency Data Handling

The script is designed to process a continuous stream of measurements arriving at approximately **10 Hz**.

Rather than initiating each measurement, the datalogger receives messages generated by the LI-COR device.

This is an important distinction from traditional Modbus-based measurement applications, where the datalogger controls when a sensor is queried.

The script uses a short delay between iterations:

```python
logger.delay_ms(10)
```

The 10 ms delay provides basic loop pacing while allowing the script to process an incoming data stream with a nominal 100 ms message interval.

The serial read operation may block for up to 150 ms, depending on data availability.

**Timing limitation:** The script does not enforce an exact 100 ms acquisition interval. Measurement timing is controlled by the external LI-COR device, while SmartObserverPlus receives and processes the transmitted messages.

The receive buffer allows multiple complete messages to be processed during a single iteration, reducing the risk of losing measurements when serial reads do not align with message boundaries.

## SmartObserverPlus Python APIs Demonstrated

| Module | Function | Purpose |
|---|---|---|
| `serial` | `configure()` | Configure the RS-232 interface |
| `serial` | `read()` | Receive incoming serial data |
| `logger` | `delay_ms()` | Control execution-loop pacing |
| `json` | `loads()` | Parse received JSON messages |

The example also demonstrates standard Python techniques for persistent byte buffering, message framing, and dictionary-based measurement mapping.

## Important Notes

- The script uses a continuous execution loop rather than the standard SmartObserverPlus lifecycle hooks.
- Measurement frequency is controlled by the LI-COR device, not by the datalogger.
- The script supports JSON messages that are split across multiple serial reads.
- Incomplete messages are retained in the receive buffer until additional data arrives.
- Invalid JSON messages are ignored.
- The script extracts the `crc32` field but does not calculate or validate the CRC.
- The script currently prints selected measurement values rather than storing them in the SmartObserverPlus internal datalog.
- The script does not transmit the received measurements to Hydroview or another server.
- The script does not implement watchdog handling or automatic recovery.