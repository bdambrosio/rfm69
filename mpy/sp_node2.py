#!/usr/bin/env python

# Sample Moteino RFM69 Node sketch, with ACK and optional encryption
# Ported from Felix Rusu's original example code.

from machine import Pin
from radios import rfm69
import time

NODEID			= 2    #unique for each node on same network
PARTNERID       = 1
NETWORKID		= 61  #the same on all nodes that talk to each other

#FREQUENCY		= rfm69.RF69_433MHZ
#FREQUENCY		= rfm69.RF69_868MHZ
FREQUENCY		= rfm69.RF69_915MHZ
ENCRYPTKEY		= "sampleEncryptKey" #exactly the same 16 characters/bytes on all nodes!
IS_RFM69HW		= False #uncomment only for RFM69HW! Leave out if you have RFM69W!
ACK_TIME		= 30 # max # of ms to wait for an ack
RETRIES			= 2
IS_RFM69HW      = True

def main():
    radio = rfm69.RFM69(isRFM69HW=True, cs=2, irq=3)
    radio.initialize(FREQUENCY,NODEID,NETWORKID)
    #radio.readAllRegs()
    print ("Operating at {} Mhz...".format(915))
	
    lastPeriod = 0
    sendSize = 5
    time.sleep(2)
    cnt=1
    while True:
        #check for any received packets
        rrd = radio.receiveDone()
        if rrd:
            if (radio.ACKRequested()):
                radio.sendACK()
            print ("ack sent",sender, msg)
            msg = radio.DATA[0:radio.DATALEN]
            sender = radio.SENDERID
            msg_len=radio.DATALEN
            cnt=cnt+1
            if radio.sendWithRetry(PARTNERID, msg.decode('utf-8'), msg_len, retries=RETRIES, retryWaitTime=ACK_TIME):
                print ("   echo success")

main()
