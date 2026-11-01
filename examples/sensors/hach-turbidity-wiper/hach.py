# A Micropython script for Geolux SmartObserverPlus datalogger
#
# This script activates wiper of a Hach solitax sc tubidity sensor, just after it 
# is powered-up by the datalogger, by writing into Modbus control register. The script uses 
# on_line_power_up hook callback function.
#

import logger
import serial
import modbus
import json

def on_line_power_up(line, instruments_on_this_line):
    port_map = {  0: serial.RS485_1, 1: serial.RS485_2, 2: serial.RS485_3 }
    stopbits_map = {  0: serial.STOP_ONE, 1: serial.STOP_TWO }
    parity_map = { 0: serial.PARITY_NONE, 1: serial.PARITY_EVEN, 2: serial.PARITY_ODD}
    
    for instr in instruments_on_this_line:
        for val in instr['Values']:
            if val['Unit'] == 'FNU':
                config = instr["Interface"]["Config"]
                print("Found turbidity sensor, activating wiper")
                logger.delay_ms(2000)
                port = port_map.get(config["Port"], serial.RS485_1)
                stop_bits = stopbits_map.get(config["Stopbits"], serial.STOP_ONE)
                parity = parity_map.get(config["Parity"], serial.PARITY_NONE)

                
                serial.configure(port, config['Baud'], parity, serial.DATA_EIGHT, stop_bits)                
                modbus.write_holding_registers(config['Port'], int(config['Address']), 21, [1])
                logger.delay_ms(5000)
                modbus.write_holding_registers(config['Port'], int(config['Address']), 21, [0])                
                break