#!/usr/bin/env python

# Sample Moteino RFM69 Node sketch, with ACK and optional encryption
# Ported from Felix Rusu's original example code.

from machine import Pin
import radios
from radios import rfm69
from radios import rfm69_registers
import time

NODEID		= 2    #unique for each node on same network
PARTNERID       = 1
NETWORKID	= 61  #the same on all nodes that talk to each other
FREQUENCY	= rfm69.RF69_915MHZ
ENCRYPTKEY	= "sampleEncryptKey" #exactly the same 16 characters/bytes on all nodes!
IS_RFM69HW	= False #uncomment only for RFM69HW! Leave out if you have RFM69W!
ACK_TIME	= 100 # max # of ms to wait for an ack
RETRIES		= 2
IS_RFM69HW      = True

def main():
    radio = rfm69.RFM69(isRFM69HW=True, csPin=3, intPin=2, rstPin=5)
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
            msg = radio.DATA[0:radio.DATALEN]
            sender = radio.SENDERID
            msg_len=radio.DATALEN
            if (radio.ACKRequested()):
                radio.sendACK()
            print ("ack sent",sender, msg.decode('utf-8'))
            cnt=cnt+1
            ack = False
            radio.send(PARTNERID, msg.decode('utf-8'), msg_len, True)
            if radio.ACKReceived(PARTNERID):
                ack = True
            else:
                ack_start = time.time()
                while (time.time()-ack_start) < .1:
                    if radio.ACKReceived(PARTNERID):
                        ack=True
                        continue
                    else:
                        time.sleep(.01)
            if ack:
                print (" echo success")
            else:
                print("  no ack from echo")

main()
