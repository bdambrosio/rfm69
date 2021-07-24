#!/usr/bin/env python

# bme680/RFM69 indoor sensor 

from bme680 import *
from machine import I2C, Pin
from radios import rfm69
import utime as time
import ujson as json
import gc

NODEID		= 2    #unique for each node on same network
PARTNERID       = 1
NETWORKID	= 61  #the same on all nodes that talk to each other

FREQUENCY	= rfm69.RF69_915MHZ
IS_RFM69HW	= True #uncomment only for RFM69HW! Leave out if you have RFM69W!
ACK_TIME	= 30 # max # of ms to wait for an ack
RETRIES		= 2
IS_RFM69HW      = True


# note below scl/sda is for Sparkfun RP2040 pro micro QWIC connector
bme = BME680_I2C(I2C(0, scl=Pin(17), sda=Pin(16)), refresh_rate=.2)
print("sensor initialized")

print(bme.temperature, bme.humidity, bme.pressure, bme.gas)
time.sleep(1)
    
def main():
	msg_id=0
        radio = rfm69.RFM69(isRFM69HW=True, csPin=3, intPin=2, rstPin=5)
        radio.initialize(FREQUENCY,NODEID,NETWORKID)
        print ("Operating at {} Mhz...".format(915))

        time.sleep(1)
        payload = [{},{},{},{}]
	while True:
            payload[0]['msg_id'] = msg_id
            payload[0]['measure'] = 'tmp'
            payload[0]['value'] = bme.temperature
            msg_id+=1

            payload[1]['msg_id'] = msg_id
            payload[1]['measure'] = 'hum'
            payload[1]['value'] = bme.humidity
            msg_id+=1

            payload[2]['msg_id'] = msg_id
            payload[2]['measure'] = 'atmp'
            payload[2]['value'] = bme.pressure
            msg_id+=1

            payload[3]['msg_id'] = msg_id
            payload[3]['measure']  = 'vols'
            payload[3]['value']  = bme.gas
            msg_id+=1

            for i in range(0,4):
                data = json.dumps(payload[i])
                print("")
	        print("Sending: {} ".format( data))
	        ack = False
                radio.send(PARTNERID, data, len(data), True)
                if radio.ACKReceived(PARTNERID):
		    ack=True
	        else:
                    for i in range(50):
                        if radio.ACKReceived(PARTNERID):
                            ack = True
                            break
                        else:
                            time.sleep(.01)
                print("  ack: ", ack)
                time.sleep(.1) #between packets of a measurement

            time.sleep(10) # between measurements
            gc.collect()

print("init")
s=time.ticks_ms()
print("hi")
print("bye")
t = time.ticks_ms()
print("time: ", t-s)
main()
