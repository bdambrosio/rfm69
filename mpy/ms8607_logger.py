#!/usr/bin/env python

# ms8607/RFM69 indoor sensor 

import ms8607
import machine
from machine import I2C, Pin
from radios import rfm69
import utime as time
import ujson as json
import gc
import neopixel as np


NODEID      = 3    #unique for each node on same network
PARTNERID   = 1
NETWORKID   = 61  #the same on all nodes that talk to each other

FREQUENCY   = rfm69.RF69_915MHZ
IS_RFM69HW  = True #uncomment only for RFM69HW! Leave out if you have RFM69W!
ACK_TIME    = 30 # max # of ms to wait for an ack
RETRIES     = 2
IS_RFM69HW      = True

np.pixels_set(0, np.COLORS[1]) # red
np.pixels_show()

# note below scl/sda is for Sparkfun RP2040 pro micro QWIC connector
ms8607 =ms8607.MS8607(I2C(0, scl=Pin(17), sda=Pin(16)))

print("sensor initialized")
print(ms8607.read_temperature_pressure(), ms8607.read_humidity())
def flash():
    for color in np.COLORS:         
        np.pixels_fill(color)  
        np.pixels_show()  
        time.sleep(0.05)
    np.pixels_set(0, np.COLORS[1]) # red
    np.pixels_show()
    

flash() # bme initialized

time.sleep(2)
msg_id=0
radio = rfm69.RFM69(isRFM69HW=True, csPin=3, intPin=2, rstPin=5, debug=False)
radio.initialize(FREQUENCY,NODEID,NETWORKID)

print("radio initialized")
flash() # radio initialized
time.sleep(2)
time_of_last_xmit = 0

def report():
    global time_of_last_xmit
    payload = [{},{},{}]
    msg_id=0
    #print("get sensor data...")
    try:
        cTemp, fTemp, pressure = ms8607.read_temperature_pressure()
        humidity = ms8607.read_humidity()
        #print("got it, formatting...")
        payload[0]['msg_id'] = msg_id
        payload[0]['measure'] = 'tmp'
        payload[0]['value'] = cTemp
        msg_id+=1

        payload[1]['msg_id'] = msg_id
        payload[1]['measure'] = 'hum'
        payload[1]['value'] = humidity
        msg_id+=1

        payload[2]['msg_id'] = msg_id
        payload[2]['measure'] = 'atmp'
        payload[2]['value'] =pressure
        msg_id+=1
        
        np.pixels_set(0, np.COLORS[3]) # green, data acquired
        np.pixels_show()
        
        print("formatted, sending", payload)
        time_of_last_xmit = int(time.time())
        for i in range(3):
            data = json.dumps(payload[i])
            #print("Sending: {} ".format( data))
            ack = False
            radio.send(PARTNERID, data, len(data), True)
            if radio.ACKReceived(PARTNERID):
                ack=True
            else:
                for i in range(5):
                    if radio.ACKReceived(PARTNERID):
                        ack = True
                        break
                    else:
                        time.sleep(.01)
            print("  ack: ", ack)
            time.sleep(.1) #between packets of a measurement
        flash() # data sent
    except Exception as e: #attempt to fetch and report measurements failed
        print(str(e))
        for i in range(3):
            np.pixels_set(0, np.COLORS[5]) # exception in data acquisition
            np.pixels_show()
            time.sleep(.2)
            np.pixels_set(0, np.COLORS[0]) # exception in data acquisition
            np.pixels_show()
            time.sleep(.1)            

def main():
    while True:
        report()
        time.sleep(10)
    
main()
