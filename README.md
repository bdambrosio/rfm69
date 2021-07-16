# rfm69
Python3 and micropython (1.15) code for RFM69 - Pi0/4 &lt;-> Pico/SparkfunProMicro!

mpy dir contains micropython code. etrombly (with recent python3 mods) python code converted to micropython 1.15.

py dir contains a couple of client python3 scripts plus a lightly modified version of
kitterly (rpi-rfm69) port of etrombly. 

**Notes:**
1. While python side supports the 'packet' object, the micropython side does not. Probably easy to add, but smaller as is. Note this means you need to grab data on micropython side quickly, see 'echo.py' as an example

2. Micropython machine.SPI, does NOT use std RP2040 spi0 pins as shown on Sparkfun RP2040 Pro Micro. This caused me no end of confusion initially. '>>>from machine import SPI', '>>>spi=SPI(id=0)', '>>>spi' will show you something like: SPI(0, baudrate=992063, polarity=0, phase=0, bits=8, sck=6, mosi=7, miso=4)

3. Micropython spi doesn't support xfer, and wants objects that support the buffer protocol. I've made minimal mods just to get this running, probably at the expense of far more allocation/garbage-generation than necessary. Future commits (soon!) will clean up some of that. 
  
4. For python side I used spi1 to leave spi0 open for display/etc. This means you need to add a spi1-1cs (or -2cs or -3cs) to /boot/config.txt, or sudo dtoverlay spi1-1cs
  
5. RPi-rfm69 needed a short delay before sending ack so that sparkfun RP2040 pro micro would see the ack. You may need a longer delay if running a different micro, or. Not well tested (eg, I tested without encryption)
  
6. This library uses interrputs, need to define reset, cs, and interrupt pins on both sides
7. Thanks to both etrombly and Kitterly for the starting points. I'm not an open-source guru, apologies to anyone if I've violated any protocols about using their code, let me know and I'll fix.
  
 
