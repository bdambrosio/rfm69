#!/usr/bin/env python3

from radios import rfm69
import datetime
import time
import RPi.GPIO as GPIO
from icecream import ic
import gc
import paho.mqtt.client as mqtt
import json
import sys
from time import ctime
from datetime import datetime
from datetime import timedelta
import pytz
import math
import subprocess

NODEID		= 1    #unique for each node on same network
PARTNERID       = 2
NETWORKID	= 61  #the same on all nodes that talk to each other
FREQUENCY	= rfm69.RF69_915MHZ
ENCRYPTKEY	= "sampleEncryptKey" #exactly the same 16 characters/bytes on all nodes!
ACK_TIME	= 40 # max # of ms to wait for an ack
RETRIES		= 2
IS_RFM69HW      = True

GPIO.cleanup()
mqtt_status = False

ptz = pytz.timezone('America/Los_Angeles')
utc = pytz.timezone('UTC')

def on_message(client, userdata, msg):
    print("mqtt callback: ", msg.topic, msg.payload)
    pass

def on_connect(client, userdata, rc):
    global mqtt_status
    mqtt_status = 'True'
    print("MQTT connect", rc)

def on_disconnect(client, userdata, rc):
    print("unexpected MQTT disconnect", rc)
    mqtt_status = False
    while mqtt_status == False:
        rc = mqtt_client.reconnect()
        if rc == 0:
            mqtt_status = True
        else:
            time.sleep(5)

# start mqtt client
mqtt_client=mqtt.Client('rfm_broker')
# Print diagnostic messages when retries/reconnects happens
mqtt_client.on_message = on_message
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
# now actually establish initial connection
#print("New session being set up")
mqtt_client.username_pw_set('mosq', '1947nw')
mqtt_client.connect('192.168.1.101')
mqtt_payload = {'measure':'', 'value':0}

radio = rfm69.RFM69(isRFM69HW=True, rstPin=36, intPin=29, csPin=24, debug=False)
radio.initialize(rfm69.RF69_915MHZ, NODEID, NETWORKID)
radio.setPowerLevel(50)
radio._receiveBegin()

last_msg_time = utc.localize(datetime.utcnow())

while True:
    now = utc.localize(datetime.utcnow())
    if now-last_msg_time > timedelta(minutes=20):
        print("restarting")
        subprocess.call(["sudo", "systemctl", "restart", "rfmBroker.service"])

    #check for any received packets
    if radio._RECEIVE_DONE:
        msg = radio.DATA
        sender = radio.SENDERID
        msg_len=radio.DATALEN
        try:
            msg = json.loads("".join(map(chr,msg)))
            measure = msg['measure']
            value = msg['value']
            mqtt_payload['measure'] = measure
            mqtt_payload['value'] = value
            mqtt_msg = json.dumps(mqtt_payload)
            mqtt_client.publish(topic='home/sensor'+str(sender)+'/'+measure,payload=mqtt_msg)
            #print(sender, msg)
            last_msg_time = utc.localize(datetime.utcnow())
        except ValueError as e:
            print('corrupt json',e,msg)
            pass
        except KeyError as e:
            #print("missing key: ", e)
            pass
        except OSError as e:
            #print('error handling radio msg', e, msg)
            pass
        radio._receiveBegin()

                                
