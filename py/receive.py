#!/usr/bin/env python3

from RFM69 import Radio, FREQ_915MHZ
import datetime
import time
import RPi.GPIO as GPIO
from icecream import ic

network_id = 61
node_id = 1
is_rfm_69HW = True

try:
    with Radio(FREQ_915MHZ, node_id, network_id, spiBus=1, resetPin=36, interruptPin=29,
               isHighPower=True, verbose=True) as radio:
        radio.set_power_level(50)
        while True:
            time.sleep(.05)
            waiting_echo = 0
            radio.begin_receive()
            while waiting_echo < 4:
                if radio.has_received_packet():
                    ic(radio.get_packets(), waiting_echo)
                    continue
                else:
                    waiting_echo += 1
                    time.sleep(.05)


except OSError as e:
    print("shutting down", e)
finally:
    GPIO.cleanup()
                                
