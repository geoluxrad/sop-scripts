# This script reads Anemometer data 10 times per second, accurately, 
# and delivers it via UDP to the connected server.

import gc
import udp
import logger
import sntp_client
import modbus
import serial
import output_power

# Script settings
server = "10.10.10.5"
port = 8080
sntp_server = "pool.ntp.org:123"
do_sync_time = False

def sync_time():
    if do_sync_time:
        server_timestamp = sntp_client.get_timestamp(logger.NETIF_ETHERNET, sntp_server)
        if server_timestamp > 0:
            logger.set_time_utc(server_timestamp)
            print("Sync time: ", server_timestamp)



logger.watchdog_enable(5 * 60)

downcount_to_timesync = 10000

msg_count = 1

# turn on power for anemometer
output_power.set(0, True)

# configure serial port for modbus
serial.configure(serial.RS485_1, 19200, serial.PARITY_NONE, serial.DATA_EIGHT, serial.STOP_ONE)

extra_time_to_compensate = 0

try:
    while True:
        cycle_start_time = logger.get_tick_count()

        # reset Python watchdog
        gc.collect()

        # reset watchdog
        logger.watchdog_reset()

        # make measurement
        # input 6 = curent wind speed uint 
        # input 7 = deirection
        output = modbus.read_input_registers(0, 1, 6 , 2)

        if output['status'] == 0:
            speed = int(output['values'][0]) / 100.0
            direction = int(output['values'][1]) / 100.0

            # format message
            message = str(msg_count) + ",8,1,"+ str(speed) + "," + str(direction) + "#"
            msg_count = msg_count + 1
            chksum = 0
            for c in message:
                chksum += ord(c)

            message = "$" + str(chksum) + "," + message
            print(message)

            # Send data 
            udp.send(logger.NETIF_ETHERNET, server, port, message)

        # time sync if needed
        downcount_to_timesync -= 1
        if downcount_to_timesync == 0:
            sync_time()
            downcount_to_timesync = 10000

        cycle_end_time = logger.get_tick_count()

        if (cycle_end_time > cycle_start_time) and (cycle_end_time - cycle_start_time < 100):
            sleep_time = 100 - (cycle_end_time - cycle_start_time)
            
            if extra_time_to_compensate > 0:
                if sleep_time >= extra_time_to_compensate:
                    sleep_time -= extra_time_to_compensate
                    extra_time_to_compensate = 0
                else:
                    sleep_time = 0
                    extra_time_to_compensate -= sleep_time
            
            if sleep_time > 0:
                logger.delay_ms(sleep_time)
        elif (cycle_end_time > cycle_start_time) and (cycle_end_time - cycle_start_time < 150):
            extra_time_to_compensate += cycle_end_time - cycle_start_time - 100
    
except:
    print("Exception")