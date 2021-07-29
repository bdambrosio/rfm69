#!/usr/bin/env python

# bme680/RFM69 indoor sensor 
#https://randomnerdtutorials.com/bme680-sensor-arduino-gas-temperature-humidity-pressure/
from bme680 import *
import machine
from machine import I2C, Pin
from radios import rfm69
import utime as time
import ujson as json
import gc
import np

NODEID      = 2    #unique for each node on same network
PARTNERID       = 1
NETWORKID   = 61  #the same on all nodes that talk to each other

FREQUENCY   = rfm69.RF69_915MHZ
IS_RFM69HW  = True #uncomment only for RFM69HW! Leave out if you have RFM69W!
ACK_TIME    = 30 # max # of ms to wait for an ack
RETRIES     = 2
IS_RFM69HW      = True

np.pixels_set(0, np.COLORS[1]) # red
np.pixels_show()

# note below scl/sda is for Sparkfun RP2040 pro micro QWIC connector
bme = BME680_I2C(I2C(0, scl=Pin(17), sda=Pin(16)), refresh_rate=.1)
bme.temperature_oversample = 8
bme.humidity_oversample = 2
bme.pressure_0versample = 4
bme.filter_size = 7
#bme.setGasHeater(320, 150); # 320*C for 150 ms

#print("sensor initialized")
#print(bme.temperature, bme.humidity, bme.pressure, bme.gas)
def flash():
    for color in np.COLORS:         
        np.pixels_fill(color)  
        np.pixels_show()  
        time.sleep(0.1)
    np.pixels_set(0, np.COLORS[1]) # red
    np.pixels_show()
    

flash() # bme initialized

time.sleep(2)
msg_id=0
radio = rfm69.RFM69(isRFM69HW=True, csPin=3, intPin=2, rstPin=5)
radio.initialize(FREQUENCY,NODEID,NETWORKID)

flash() # radio initialized
time.sleep(2)

def report():
    payload = [{},{},{},{}]
    msg_id=0
    for i in range(2):
        try:
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
        
            np.pixels_set(0, np.COLORS[3]) # green, data acquired
            np.pixels_show()
            time.sleep(.5)
        
            for i in range(0,4):
                data = json.dumps(payload[i])
                #print("")
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
                #print("  ack: ", ack)
                time.sleep(.1) #between packets of a measurement
            flash() # data sent
        except: #attempt to fetch and report measurements failed
            for i in range(3):
                np.pixels_set(0, np.COLORS[5]) # exception in data acquisition
                np.pixels_show()
                time.sleep(.2)
                np.pixels_set(0, np.COLORS[0]) # exception in data acquisition
                np.pixels_show()
                time.sleep(.1)
            
        time.sleep(10) # between measurements
        #gc.collect()

def main():
    report()
    machine.deepsleep(600)
    
main()
