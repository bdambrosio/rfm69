#!/usr/bin/env python

# bme680/RFM69 indoor sensor 

from bme680 import *
from machine import I2C, Pin
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
ACK_TIME		= 50 # max # of ms to wait for an ack
RETRIES			= 5
TRANSMITPERIOD		= 150 #transmit a packet to gateway so often (in ms)
payload			= "123 ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LED_PIN 		= Pin(25, Pin.OUT)
IS_RFM69HW              = True

bme = BME680_I2C(I2C(0), refresh_rate=1)

def main():
	radio = rfm69.RFM69(isRFM69HW=True, cs=2, irq=3)
	radio.initialize(FREQUENCY,NODEID,NETWORKID)
        #radio.readAllRegs()
	print ("Operating at {} Mhz...".format(915))
	
	lastPeriod = 0
	sendSize = 0
        time.sleep(1)
	while True:
		"""#check for any received packets
        time.sleep(.05)
        rrd = radio.receiveDone()
        if rrd:
			if (radio.ACKRequested()):
				radio.sendACK()
				print (" - ACK sent")
			print ("from {} {} bytes {} [RX_RSSI: {}]".format(radio.SENDERID, radio.DATALEN, radio.DATA[0:radio.DATALEN], radio.RSSI))
			print ("from [{}] {} [RX_RSSI: {}]".format(radio.SENDERID, radio.DATA[0:radio.DATALEN], radio.RSSI))
        """
		currPeriod = radio.millis()/TRANSMITPERIOD
		if (currPeriod != lastPeriod):
			lastPeriod = currPeriod
			s = "Sending[{}]: {} ".format(sendSize, payload[:sendSize])
			if (radio.sendWithRetry(PARTNERID, payload, sendSize, retries=RETRIES, retryWaitTime=ACK_TIME)):
				s += "ok!"
			else:
				s += "nothing..."
			print (s)
			sendSize = (sendSize + 1) % 5

main()
