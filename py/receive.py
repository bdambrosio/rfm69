#!/usr/bin/env python3

from RFM69 import Radio, FREQ_915MHZ
import datetime
import time
import RPi.GPIO as GPIO
from icecream import ic
import gc

network_id = 61
node_id = 1
is_rfm_69HW = True

try:
    with Radio(FREQ_915MHZ, node_id, network_id, spiBus=1, resetPin=36, interruptPin=29,
               isHighPower=True, verbose=False) as radio:
        radio.set_power_level(50)
        while True:
            radio.begin_receive()
            while (not radio.has_received_packet()):
                    time.sleep(.05) # nothing to do, sleep
            packet = radio.get_packets()[0]
            ic(packet.sender, packet.data_string)
            gc.collect()

except OSError as e:
    print("shutting down", e)
finally:
    GPIO.cleanup()
                                
