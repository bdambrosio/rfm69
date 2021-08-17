#!/usr/bin/env python

# ms8607/RFM69 indoor sensor 

import machine
from machine import I2C, Pin, RTC
from radios import rfm69
import utime as time
import ujson as json
import gc
import dht
import pins

NODEID      = pins.NODEID    #unique for each node on same network
PARTNERID   = 1
NETWORKID   = 61  #the same on all nodes that talk to each other

FREQUENCY   = rfm69.RF69_915MHZ
IS_RFM69HW  = True #uncomment only for RFM69HW! Leave out if you have RFM69W!
ACK_TIME    = 30 # max # of ms to wait for an ack
RETRIES     = 2
IS_RFM69HW      = True

dht22=dht.DHT22(Pin(pins.am2302))
#dht22=am2320.AM2320(I2C(1))
#print("sensor initialized")

msg_id=0
radio = rfm69.RFM69(isRFM69HW=True, spiBus=pins.rfm69SpiBus, csPin=pins.rfm69NSS, intPin=pins.rfm69D0, rstPin=pins.rfm69RST, debug=False)
radio.initialize(FREQUENCY,NODEID,NETWORKID)

print("radio initialized")
time.sleep(1)
time_of_last_xmit = 0
#wdt = WDT(timeout=32000)
#try:
#    RTC.cancel()
#except:
#    pass


def report(wakeup):
    dht22=dht.DHT22(Pin(pins.am2302))
    #dht22=am2320.AM2320(I2C(1))
    #print("sensor initialized")

    msg_id=0
radio = rfm69.RFM69(isRFM69HW=True, spiBus=pins.rfm69SpiBus, csPin=pins.rfm69NSS, intPin=pins.rfm69D0, rstPin=pins.rfm69RST, debug=False)
    radio.initialize(FREQUENCY,NODEID,NETWORKID)
    print("radio initialized")
    time.sleep(1)
    payload = [{},{},{}]
    msg_id=0
    #print("get sensor data...")
    try:
        dht22.measure()
        cTemp = dht22.temperature()
        humidity = dht22.humidity()
        #print("got it, formatting...")
        payload[0]['msg_id'] = msg_id
        payload[0]['measure'] = 'tmp'
        payload[0]['value'] = cTemp
        msg_id+=1

        payload[1]['msg_id'] = msg_id
        payload[1]['measure'] = 'hum'
        payload[1]['value'] = humidity
        msg_id+=1

        print("formatted, sending", payload)
        time_of_last_xmit = int(time.time())
        for i in range(2):
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
        print('data sent') # data sent
    
    except OSError as e:
        raise e
    radio.sleep()
    machine.deepsleep(360000)
 
RTC().wakeup(120000, report)

