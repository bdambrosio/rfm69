#!/usr/bin/env python3

from radios import rfm69
import datetime
import time
import RPi.GPIO as GPIO
from icecream import ic
import gc

NODEID		= 1    #unique for each node on same network
PARTNERID       = 2
NETWORKID	= 61  #the same on all nodes that talk to each other
FREQUENCY	= rfm69.RF69_915MHZ
ENCRYPTKEY	= "sampleEncryptKey" #exactly the same 16 characters/bytes on all nodes!
ACK_TIME	= 40 # max # of ms to wait for an ack
RETRIES		= 2
IS_RFM69HW      = True



try:
    radio = rfm69.RFM69(isRFM69HW=True, rstPin=36, intPin=29, csPin=24, debug=False)
    radio.initialize(rfm69.RF69_915MHZ, NODEID, NETWORKID)
    radio.setPowerLevel(50)
    radio._receiveBegin()
    while True:
        #check for any received packets
        #rrd = radio.receiveDone()
        if radio._RECEIVE_DONE:
            msg = radio.DATA
            sender = radio.SENDERID
            msg_len=radio.DATALEN
            #if (radio.ACKRequested()):
            #    time.sleep(.02)
            #    radio.sendACK()
            print(sender, "".join(map(chr,msg)))
            radio._receiveBegin()


except AttributeError as e:
    print ("Error:", e)
    raise e
finally:
    print("cleaning up")
    GPIO.cleanup()
                                
