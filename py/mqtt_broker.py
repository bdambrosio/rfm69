#!/usr/bin/env python3

from RFM69 import Radio, FREQ_915MHZ
import datetime
import time
import RPi.GPIO as GPIO
from icecream import ic
import logging

network_id = 61
node_id = 1
is_rfm_69HW = True

try:
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    with Radio(FREQ_915MHZ, node_id, network_id, spiBus=1, resetPin=36, interruptPin=29,
               isHighPower=True, verbose=False) as radio:
        radio.set_power_level(50)
        while True:
            radio.begin_receive()
            for waiting in range(4 ):
                if radio.has_received_packet():
                    packets = radio.get_packets()
                    for packet in packets:
                        if radio.send(packet.sender, packet.data_string, require_ack=True):
                            print("echo ack recieved")
                        logger.debug(str(packet.sender)+" "+ packet.data_string)
                    break
                else:
                    time.sleep(.05)


except OSError as e:
    print("shutting down", e)
finally:
    GPIO.cleanup()
                                
