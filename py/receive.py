#!/usr/bin/env python3

from radios import rfm69
import datetime
import time
import RPi.GPIO as GPIO
from icecream import ic
import gc

NODEID		= 4    #unique for each node on same network
PARTNERID       = 2
NETWORKID	= 61  #the same on all nodes that talk to each other
FREQUENCY	= rfm69.RF69_915MHZ
ENCRYPTKEY	= "sampleEncryptKey" #exactly the same 16 characters/bytes on all nodes!
ACK_TIME	= 40 # max # of ms to wait for an ack
RETRIES		= 2
IS_RFM69HW      = True



try:
    radio = rfm69.RFM69(isRFM69HW=True, rstPin=36, intPin=29)
    radio.initialize(rfm69.RF69_915MHZ, NODEID, NETWORKID)
    radio.set_power_level(50)
    while True:
        radio.begin_receive()
        while (not radio.has_received_packet()):
            time.sleep(.05) # nothing to do, sleep
        packet = radio.get_packets()[0]
        ic(packet.sender, packet.data_string)
except AttributeError as e:
    print ("Error:", e)
    raise e
finally:
    print("cleaning up")
    GPIO.cleanup()
                                
