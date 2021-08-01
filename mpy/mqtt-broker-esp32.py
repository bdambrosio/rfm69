#!/usr/bin/env python

# Sample Moteino RFM69 Node sketch, with ACK and optional encryption
# Ported from Felix Rusu's original example code.

import network
import machine
import sys
from machine import Pin
import radios
from radios import rfm69
from radios import rfm69_registers
import json
import umqtt.simple as mqtt
import time
from boot import ssid, password

NODEID      = 1    #unique for each node on same network
PARTNERID       = 2
NETWORKID   = 61  #the same on all nodes that talk to each other
FREQUENCY   = rfm69.RF69_915MHZ
ENCRYPTKEY  = "sampleEncryptKey" #exactly the same 16 characters/bytes on all nodes!
IS_RFM69HW  = False #uncomment only for RFM69HW! Leave out if you have RFM69W!
ACK_TIME    = 100 # max # of ms to wait for an ack
RETRIES     = 2
IS_RFM69HW      = True

#get network object so we can check connection status
sta_if = network.WLAN(network.STA_IF);

def mqtt_cb(topic, msg):
    #print("mqtt callback: ", topic, msg)
    pass
    
def main():
    # start mqtt client
    mqtt_client=mqtt.MQTTClient('pvDisplay_mqtt', '192.168.1.101', user='mosq', password='1947nw')
    # Print diagnostic messages when retries/reconnects happens

    mqtt_client.set_callback(mqtt_cb)
    # now actually establish initial connection
    #print("New session being set up")
    mqtt_client.connect()
    mqtt_payload = {'measure':'', 'value':0}
    
    radio = rfm69.RFM69(isRFM69HW=True, spiBus=2, csPin=5, intPin=34, rstPin=33, debug=True)
    radio.initialize(FREQUENCY,NODEID,NETWORKID)
    #print ("Operating at {} Mhz...".format(915))
    radio._receiveBegin()
    while True:
        try:
            if not sta_if.isconnected():
                print("network connection lost")
                while not sta_if.isconnected():
                    sta_if.connect(ssid, password)
                mqtt_client.reconnect()
                print("reconnected")
        except:
            continue
        #check for any received packets
        rrd = radio.receiveDone()
        if rrd:
            print(radio.DATA[0:radio.DATALEN])
            rvcd_msg = radio.DATA[0:radio.DATALEN]
            sender = radio.SENDERID
            msg_len=radio.DATALEN
            if (radio.ACKRequested()):
                radio.sendACK()
            try:
                msg = json.loads(rvcd_msg)
                measure = msg['measure']
                value = msg['value']
                mqtt_payload['measure'] = measure
                mqtt_payload['value'] = value
                mqtt_msg = json.dumps(mqtt_payload)
                mqtt_client.publish(topic='home/sensor'+str(sender)+'/'+measure,
                                    msg=mqtt_msg)
            except ValueError as e:
                print('corrupt json',e,msg)
                pass
            except KeyError as e:
                pass
                #print("missing key: ", e)
            except OSError as e:
                pass
                #print('error handling radio msg', e, msg)
            except Error as e:
                print ('error', e)

main()
