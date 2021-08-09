# rfm69
Python3 and micropython (1.15) code for RFM69 - Pi0/4 &lt;-> Pi0 <-> RPi Pico / ESP32 / STM32 BlackPill ...
Why RFM69 in these days of LORA? RFM69 modules are cheaper, more than good enough for local home-based sensors, just about as low power. I used Sparkfun sourced Hope RFM69HCWs

mpy dir contains micropython code. WCalvert python code converted to micropython 1.15.

py dir contains a couple of client python3 scripts plus an updated version of WCalvert python code (https://github.com/wcalvert/rfm69-python). py 'radios' dir contains WCalvert code converted to Python3 for the RPi.

**Notes:**
1. No support for 'packet' objects. Probably easy to add, but smaller as is. Note this means you need to grab data on micropython side quickly, see 'echo.py' as an example

2. Micropython machine.SPI, does NOT use std RP2040 spi0 pins as shown on Sparkfun RP2040 Pro Micro. This caused me no end of confusion initially. '>>>from machine import SPI', '>>>spi=SPI(id=0)', '>>>spi' will show you something like: SPI(0, baudrate=992063, polarity=0, phase=0, bits=8, sck=6, mosi=7, miso=4)

3. Micropython spi doesn't support xfer, and wants objects that support the buffer protocol. I've made minimal mods just to get this running, probably at the expense of far more allocation/garbage-generation than necessary. Future commits (soon!) will clean up some of that. On the other hand, needed to use xfer on Python3 side to get register reads to work.
  
4. For python side I used spi0 (default). If you need this for other uses, you need to add a spi1-1cs (or -2cs or -3cs) to /boot/config.txt, or sudo dtoverlay spi1-1cs
  
5. RPi-rfm69 may need a short delay before sending ack so that mcu side would see the ack. You may need a longer delay if running a different micro, or. Not well tested (eg, I tested without encryption)
  
6. This library uses interrputs, need to define reset, cs, and interrupt pins on both sides

8. Thanks to both WCalvert and Kitterly for the starting points. Mostly this is a port of WClavert's python clone of Felix Rusu's RFM69 library. I'm not an open-source guru, apologies to anyone if I've violated any protocols about using their code, let me know and I'll fix.
  
 
