import json
import time
import paho.mqtt.client as mqtt
import asyncio
from RFM69 import Radio, FREQ_915MHZ
from icecream import ic

async def call_API(url, packet):
    async with ClientSession() as session:
        print("Sending packet to server")
        async with session.post(url, json=packet.to_dict('%c')) as response:
            response = await response.read()
            print("Server responded", response)

async def receiver(radio):
    while True:    
        for packet in radio.get_packets():
            ic("Packet received", packet.data_string)
        await asyncio.sleep(.1)

async def send(radio, to, message):
    print ("Sending")
    if radio.send(to, message, attempts=3, waitTime=100):
        print ("Acknowledgement received")
    else:
        print ("No Acknowledgement")
    
async def pinger(radio):
    print("Pinger")
    counter = 0
    while True:
        await send(radio, 2, "ping {}".format(counter))
        counter += 1
        await asyncio.sleep(5)

#setup to publish to mosquitto broker
def new_msg():
    print ("new msg from mqtt")
    
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        ic("MQTT connect success")
    else:
        ic(f"MQTT connect fail with code {rc}")

def on_publish(client,userdata,result):             #create function for callback
    #print("data published ", result)
    pass

client = mqtt.Client() 
client.on_connect = on_connect
client.on_message = new_msg
client.on_publish = on_publish
client.username_pw_set(username='mosq', password='1947nw')
ic("Connecting to mqtt")
client.connect("127.0.0.1", 1883, 60) 


loop = asyncio.get_event_loop()
node_id = 1
network_id = 61
with Radio(FREQ_915MHZ, node_id, network_id,  spiBus=1, resetPin=36, interruptPin=29,
           isHighPower=True, verbose=True) as radio:
    print ("radio created")
    #loop.create_task(receiver(radio))
    #loop.create_task(pinger(radio))
    ic("starting threads")
    #loop.run_forever()
    while True:
        time.sleep(.1)
        for packet in radio.get_packets():
            ic(packet, packet.data_string)

loop.close()
