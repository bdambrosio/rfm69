# Distributed with a free-will license.
# Use it any way you want, profit or free, provided it fits in the licenses of its associated works.
# MS8607_02BA
# This code is designed to work with the MS8607_02BA_I2CS I2C Mini Module available from ControlEverything.com.
# https://www.controleverything.com/products

# BDA - ported to micropython for the adafruit ms8607 QWIC module 7/31/2021

from machine import Pin, I2C
import time

class MS8607:
    def __init__(self, i2c_bus):  
        self._buf1 = bytearray([0])
        self._bus = i2c_bus
        # MS8607_02BA address, 0x76(118)
        #       0x1E(30)    Reset command
        self._buf1[0]=0x1E
        self._bus.writeto(0x76, self._buf1)

        time.sleep(0.5)

        # Read 12 bytes of calibration data
        # Pressure sensitivity | SENST1
        data1 = self._bus.readfrom_mem(0x76, 0xA2, 2)
        # Pressure offset | OFFT1
        data2 = self._bus.readfrom_mem(0x76, 0xA4, 2)
        # Temperature coefficient of pressure sensitivity | TCS
        data3 = self._bus.readfrom_mem(0x76, 0xA6, 2)
        # Temperature coefficient of pressure offset | TCO
        data4 = self._bus.readfrom_mem(0x76, 0xA8, 2)
        # Reference temperature | TREF
        data5 = self._bus.readfrom_mem(0x76, 0xAA, 2)
        # Temperature coefficient of the temperature | TEMPSENS
        data6 = self._bus.readfrom_mem(0x76, 0xAC, 2)

        # Convert the data
        self._c1 = data1[0] * 256 + data1[1]
        self._c2 = data2[0] * 256 + data2[1]
        self._c3 = data3[0] * 256 + data3[1]
        self._c4 = data4[0] * 256 + data4[1]
        self._c5 = data5[0] * 256 + data5[1]
        self._c6 = data6[0] * 256 + data6[1]

    def read_temperature_pressure(self):
        # MS8607_02BA address, 0x76(118)
        #       0x40(64)    Initiate pressure conversion(OSR = 256)
        self._buf1[0] = 0x40
        self._bus.writeto(0x76, self._buf1)
        time.sleep(0.5)
        # Read data back from 0x00(0), 3 bytes, D1 MSB2, D1 MSB1, D1 LSB
        # Digital pressure value
        data = self._bus.readfrom_mem(0x76, 0x00, 3)
        D1 = data[0] * 65536 + data[1] * 256 + data[2]

        # MS8607_02BA address, 0x76(118)
        #       0x50(64)    Initiate temperature conversion(OSR = 256)
        self._buf1[0] = 0x50
        self._bus.writeto(0x76, self._buf1)
        time.sleep(0.5)
        # Read data back from 0x00(0), 3 bytes, D2 MSB2, D2 MSB1, D2 LSB
        # Digital temperature value
        data0 = self._bus.readfrom_mem(0x76, 0x00, 3)

        # Convert the data
        D2 = data0[0] * 65536 + data0[1] * 256 + data0[2]
        dT = D2 - self._c5 * 256
        Temp = 2000 + dT * self._c6 / 8388608
        OFF = self._c2 * 131072 + (self._c4 * dT) / 64
        SENS = self._c1 * 65536 + (self._c3 * dT ) / 128

        if Temp >= 2000 :
            Ti = 5 * (dT * dT) / 274877906944
            OFFi = 0
            SENSi= 0
        elif Temp < 2000 :
            Ti = 3 * (dT * dT) / 8589934592
            OFFi= 61 * ((Temp - 2000) * (Temp - 2000)) / 16
            SENSi= 29 * ((Temp - 2000) * (Temp - 2000)) / 16
            if Temp < -1500:
                OFFi = OFFi + 17 * ((Temp + 1500) * (Temp + 1500))
                SENSi = SENSi + 9 * ((Temp + 1500) * (Temp +1500))
        OFF2 = OFF - OFFi
        SENS2= SENS - SENSi
        cTemp = (Temp - Ti) / 100.0
        fTemp =  cTemp * 1.8 + 32
        pressure = ((((D1 * SENS2) / 2097152) - OFF2) / 32768.0) / 100.0

        #print(cTemp, fTemp, pressure)
        # MS8607_02BA address, 0x40(64)
        #       0xFE(254)   Send reset command
        self._buf1[0] = 0xFE
        self._bus.writeto(0x40, self._buf1)
        time.sleep(0.3)
        return cTemp, fTemp, pressure


    def read_humidity(self):
        # MS8607_02BA address, 0x40(64)
        #       0xF5(245)   Send NO Hold master command
        self._buf1[0] = 0xF5
        self._bus.writeto(0x40, self._buf1)
        time.sleep(0.5)

        # MS8607_02BA address, 0x40(64)
        # Read data back from device
        data0 = self._bus.readfrom(0x40,1)
        data1 = 0

        # Convert the data
        D3 = data0[0] * 256 + data1

        humidity = (-6.0 + (125.0 * (D3 / 65536.0)))
        return humidity
