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
        send_cnt=0
        while True:
            time.sleep(.5)
            send_cnt += 1
            print("sending", send_cnt)
            if radio.send(2, str(send_cnt), attempts=1, waitTime=100):
                print("ack recieved")
            print("waiting for echo")
            echo_wait = 0
            radio.begin_receive()
            while echo_wait < 4:
                if radio.has_received_packet():
                    for packet in radio.get_packets():
                        ic(echo_wait, packet.sender, packet.data_string)
                    continue
                else:
                    echo_wait += 1
                    time.sleep(.05)


except OSError as e:
    print("shutting down", e)
finally:
    GPIO.cleanup()
                                
