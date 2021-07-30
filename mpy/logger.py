#!/usr/bin/env python

# bme680/RFM69 indoor sensor 
#https://randomnerdtutorials.com/bme680-sensor-arduino-gas-temperature-humidity-pressure/
import bme680
from bme680 import BME680
from bme680 import constants as bme_consts
import machine
from machine import I2C, Pin
from radios import rfm69
import utime as time
import ujson as json
import gc
import neopixel as np

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
bme = bme680.BME680(i2c_device=I2C(0, scl=Pin(17), sda=Pin(16)), i2c_addr=0x77)
bme.set_humidity_oversample(bme_consts.OS_2X)
bme.set_pressure_oversample(bme_consts.OS_4X)
bme.set_temperature_oversample(bme_consts.OS_8X)
bme.set_filter(bme_consts.FILTER_SIZE_3)

bme.set_gas_status(bme_consts.ENABLE_GAS_MEAS)
bme.set_gas_heater_temperature(320)
bme.set_gas_heater_duration(150)
bme.select_gas_heater_profile(0)

print("sensor initialized")
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
    for i in range(3):
        print("get sensor data...")
        if bme.get_sensor_data():
          if i < 1:
              print("skipping first reading")
              continue # ignore first reading
          try:
            print("got it, formatting...")
            payload[0]['msg_id'] = msg_id
            payload[0]['measure'] = 'tmp'
            payload[0]['value'] = bme.data.temperature
            msg_id+=1

            payload[1]['msg_id'] = msg_id
            payload[1]['measure'] = 'hum'
            payload[1]['value'] = bme.data.humidity
            msg_id+=1

            payload[2]['msg_id'] = msg_id
            payload[2]['measure'] = 'atmp'
            payload[2]['value'] = bme.data.pressure
            msg_id+=1

            gas_stable = bme.data.heat_stable
            if gas_stable:
                payload[3]['msg_id'] = msg_id
                payload[3]['measure']  = 'vols'
                payload[3]['value']  = bme.data.gas_resistance
                msg_id+=1
        
            np.pixels_set(0, np.COLORS[3]) # green, data acquired
            np.pixels_show()
            time.sleep(.5)
        
            print("formatted, sending")
            for i in range(0,4):
              if i < 3 or gas_stable:
                data = json.dumps(payload[i])
                #print("")
                print("Sending: {} ".format( data))
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
            
          time.sleep(1) # between measurements

def main():
    while True:
        bme. set_power_mode(bme_consts.FORCED_MODE)
        report()
        bme. set_power_mode(bme_consts.SLEEP_MODE)
        time.sleep(20)
    
main()
