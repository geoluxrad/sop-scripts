# Hach TSS Sensor Wiper Control

## Overview

This example demonstrates how to implement automatic wiper control for a Hach Solitax sc  turbidity and suspended solids sensor connected to the Geolux SmartObserverPlus datalogger.

### Requirements

The application requires automatic activation of the sensor's cleaning wiper whenever the sensor's power supply is switched on. The Hach sensor is connected to the datalogger via Modbus RTU over RS-485. The datalogger must send a Modbus command to activate the wiper, wait for the cleaning operation, and then send another command to deactivate it.

The solution should work with the standard SmartObserverPlus measurement functionality, without interfering with the datalogger's normal measurement, data logging, or communication workflow. It should automatically detect if the solitax sensor is present.

### Implementation

The application uses the standard SmartObserverPlus Python lifecycle hook `on_line_power_up()`, which is called when an instrument power line is activated.

The script identifies the turbidity sensor from the configured instruments, retrieves its Modbus communication parameters, and sends the appropriate commands to operate the wiper.

The script:

1. Uses the `on_line_power_up()` lifecycle hook to initiate the cleaning procedure when an instrument power line is activated.
2. Searches the instruments connected to that power line for a measurement with the unit `FNU` - this is a heuristical methond used to identify the turbidity sensor.
3. Retrieves the sensor's Modbus port, baud rate, parity, stop bits, and slave address from the instrument configuration.
4. Configures the corresponding RS-485 interface for Modbus RTU communication.
5. Writes value `1` to Modbus holding register `21` to activate the wiper, for 5 seconds.

The script integrates with the standard SmartObserverPlus measurement workflow, by implementing only a predefined hook callback function. The datalogger continues to handle sensor measurements, data storage, and communication using its built-in functionality.

## Hardware Setup

- Geolux SmartObserverPlus datalogger
- Hach turbidity / suspended solids sensor with Modbus RTU interface and integrated cleaning wiper
- Sensor power supply connected to a controllable power output of the datalogger

### Modbus Configuration

The script automatically retrieves the Modbus communication settings from the SmartObserverPlus instrument configuration.

The script uses the following command to activate the wiper (it writes value `1` into register 21):

```python
modbus.write_holding_registers(
    config['Port'],
    int(config['Address']),
    21,
    [1]
)
```

After a 5-second delay, it sends the same command with value `0` to deactivate the wiper.

## Instrument Identification

The script identifies the turbidity sensor by checking the units of the configured measurement values:

```python
for instr in instruments_on_this_line:
    for val in instr['Values']:
        if val['Unit'] == 'FNU':
```

The unit `FNU` (Formazin Nephelometric Units) is used for turbidity measurements.

This approach allows the script to identify the sensor automatically, without hardcoding a particular Modbus port or slave address, or relying on the sepcific instrument name being assigned to the device by the user through datalogger configurator tool.

**Note:** The script assumes that an instrument configured with a measurement in `FNU` is the Hach sensor requiring wiper control. If multiple turbidity sensors or other instruments using this unit are connected to the same power line, additional identification logic may be required.

## SmartObserverPlus Python APIs Demonstrated

| Module | Function | Purpose |
|---|---|---|
| Lifecycle hook | `on_line_power_up()` | Execute custom logic when an instrument power line is activated |
| `serial` | `configure()` | Configure the RS-485 interface |
| `modbus` | `write_holding_registers()` | Activate and deactivate the sensor wiper |
| `logger` | `delay_ms()` | Implement delays in the cleaning sequence |

## Important Notes

- The script uses a standard SmartObserverPlus lifecycle hook and does not override the default datalogger functionality.
- The sensor is identified automatically using the `FNU` measurement unit in the instrument configuration.
- Modbus communication parameters are taken from the instrument configuration rather than being hardcoded.
- The cleaning sequence is triggered by the power-line activation callback, not by a separate periodic cleaning timer.
- The script does not check the result of the Modbus write operations or verify that the wiper completed its cleaning cycle.