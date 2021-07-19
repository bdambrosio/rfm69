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
        send_cnt=0
        while True:
            time.sleep(.5)
            send_cnt += 1
            logger.debug("sending "+str(send_cnt))
            if not radio.send(2, str(send_cnt), True):
                logger.debug("   no ack from send")
            #logger.debug("waiting for echo")
            echo_wait = 0
            radio.begin_receive()
            while echo_wait < 4:
                if radio.has_received_packet():
                    for packet in radio.get_packets():
                        logger.debug("    echo "+str(echo_wait)+" "+str(packet.sender)+" "+ packet.data_string)
                    continue
                else:
                    echo_wait += 1
                    time.sleep(.05)


except OSError as e:
    print("shutting down", e)
finally:
    GPIO.cleanup()
                                
