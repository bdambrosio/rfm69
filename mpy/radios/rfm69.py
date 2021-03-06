# **********************************************************************************
# Wes Calvert, 2015
# This code ported from Felix Rusu's original work:
# https://github.com/LowPowerLab/RFM69
# **********************************************************************************
# License
# **********************************************************************************
# This program is free software; you can redistribute it 
# and/or modify it under the terms of the GNU General    
# Public License as published by the Free Software       
# Foundation; either version 2 of the License, or        
# (at your option) any later version.                    
#                                                        
# This program is distributed in the hope that it will   
# be useful, but WITHOUT ANY WARRANTY; without even the  
# implied warranty of MERCHANTABILITY or FITNESS FOR A   
# PARTICULAR PURPOSE.  See the GNU General Public        
# License for more details.                              
#                                                        
# You should have received a copy of the GNU General    
# Public License along with this program; if not, write 
# to the Free Software Foundation, Inc.,                
# 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#                                                        
# Licence can be viewed at                               
# http:#www.fsf.org/licenses/gpl.txt                    
#
# Please maintain this license information along with authorship
# and copyright notices in any redistribution of this code
# **********************************************************************************

from machine  import Pin, SPI
from radios.rfm69_registers import *
from radios.base_radio import BaseRadio
import utime as time

# to take advantage of the built in AES/CRC we want to limit the frame size to 
# the internal FIFO size (66 bytes - 3 bytes overhead)
RF69_MAX_DATA_LEN = 61 

# upper RX signal sensitivity threshold in dBm for carrier sense access
CSMA_LIMIT      = -90 
RF69_MODE_SLEEP     = 0 # XTAL OFF
RF69_MODE_STANDBY       = 1 # XTAL ON
RF69_MODE_SYNTH     = 2 # PLL ON
RF69_MODE_RX        = 3 # RX MODE
RF69_MODE_TX        = 4 # TX MODE

#available frequency bands
RF69_315MHZ     = 31  
RF69_433MHZ     = 43
RF69_868MHZ     = 86
RF69_915MHZ     = 91

# puts the temperature reading in the ballpark, user can fine tune the returned value
COURSE_TEMP_COEF    = -90
RF69_BROADCAST_ADDR = 255
RF69_CSMA_LIMIT_MS  = 1000
RF69_TX_LIMIT_MS    = 1000
RF69_FSTEP      = 61.03515625 # == FXOSC/2^19 = 32mhz/2^19 (p13 in DS)

class RFM69(BaseRadio):
    DATA = []
    DATALEN = 0
    SENDERID = 0
    TARGETID = 0
    PAYLOADLEN = 0
    ACK_REQUESTED = False
    ACK_RECEIVED = False
    RSSI = 0
    _mode = 0
    _intPin = 2
    _csPin = 3
    _address = 0
    _promiscuousMode = False
    _powerLevel = 31
    _isRFM69HW = True
    
    def __init__(self, isRFM69HW=True, spiBus=0, intPin=2, csPin=3, rstPin=5, debug=False):
        self._isRFM69HW = isRFM69HW
        
        self.spi = SPI(spiBus)
        self._intPin = Pin(intPin, Pin.IN)
        self._csPin = Pin(csPin, Pin.OUT)
        self._rstPin = Pin(rstPin, Pin.OUT)
        self.start_time = time.time()
        self._packetSentIrq = False # used to make sure we send end_of_transmit interrupt
        self._debug=debug
        
    # Convention I want to stick to is a single underscore to indicate "private" methods.
    # I'm grouping all the private stuff up at the beginning.

    def _millis(self):
        delta = time.time() - self.start_time
        return delta * 1000

    def _readReg(self, addr):
        self._select()
        self.spi.write(bytearray([addr & 0x7F]))
        result = self.spi.read(1)[0]
        self._unselect()
        return result
    
    def _writeReg(self, addr, value):
        self._select()
        self.spi.write(bytearray([addr | 0x80, value]))
        self._unselect()
        
        # Select the transceiver
    def _select(self):
        self._csPin.value(0)

    # Unselect the transceiver chip
    def _unselect(self): 
        self._csPin.value(1)
    
    def _setMode(self, newMode):
        if newMode == self._mode:
            return
        if newMode == RF69_MODE_TX:
            self._writeReg(REG_OPMODE, (self._readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_TRANSMITTER)
            if self._isRFM69HW:
                self.setHighPowerRegs(True)
        elif newMode == RF69_MODE_RX:
            self._writeReg(REG_OPMODE, (self._readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_RECEIVER)
            if self._isRFM69HW:
                self.setHighPowerRegs(False)
        elif newMode == RF69_MODE_SYNTH:
            self._writeReg(REG_OPMODE, (self._readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_SYNTHESIZER)
        elif newMode == RF69_MODE_STANDBY:
            self._writeReg(REG_OPMODE, (self._readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_STANDBY)
        elif newMode == RF69_MODE_SLEEP:
            self._writeReg(REG_OPMODE, (self._readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_SLEEP)

        # we are using packet mode, so this check is not really needed
        # but waiting for mode ready is necessary when going from sleep because the FIFO may not 
        # be immediately available from previous mode

        # Wait for ModeReady
        while (self._mode == RF69_MODE_SLEEP and (self._readReg(REG_IRQFLAGS1) & RF_IRQFLAGS1_MODEREADY) == 0x00): 
            pass
        self._mode = newMode

    def _canSend(self):
        if self._mode == RF69_MODE_STANDBY:
            self._receiveBegin()
            return True
        #if signal stronger than -100dBm is detected assume channel activity
        #DNU - will ALWAYS return true on second call, no?
        if (self._mode == RF69_MODE_RX and self.PAYLOADLEN == 0 and self.readRSSI() < CSMA_LIMIT): 
            self._setMode(RF69_MODE_STANDBY)
            return True
        return False

    def _sendFrame(self, toAddress, buffer, bufferSize, requestACK=True, sendACK=False):
        #turn off receiver to prevent reception while filling fifo
        self._setMode(RF69_MODE_STANDBY) 
        while ((self._readReg(REG_IRQFLAGS1) & RF_IRQFLAGS1_MODEREADY) == 0x00):
            pass # Wait for ModeReady

        self._writeReg(REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_00) # DIO0 is "Packet Sent"
        if bufferSize > RF69_MAX_DATA_LEN:
            bufferSize = RF69_MAX_DATA_LEN

        #write to FIFO
        self._select()
        ack = 0
        if sendACK:
            ack = 0x80
        elif requestACK:
            ack = 0x40
        self.spi.write(bytearray([REG_FIFO | 0x80, bufferSize + 3, toAddress, self._address, ack]))
        
        bufferBytes = []
        for i in range(0, bufferSize):
            self.spi.write(bytearray([ord(buffer[i])]))
        self._unselect()

        # no need to wait for transmit mode to be ready since its handled by the radio
        self._packetSentIrq = False
        self._setMode(RF69_MODE_TX)
        # wait for DIO0 to turn HIGH signalling transmission finish
        while (self._packetSentIrq == False and (self._readReg(REG_IRQFLAGS2) & RF_IRQFLAGS2_PACKETSENT == 0x00)):
            pass
        self._packetSentIrq == False
        if requestACK==True:
            self._receiveBegin()
        else:
            self._setMode(RF69_MODE_RX)

    def _interruptHandler(self, pin):
        irqFlags1 = self._readReg(REG_IRQFLAGS1)
        irqFlags2 = self._readReg(REG_IRQFLAGS2)
        if self._debug:
            print(self._mode, RF69_MODE_RX, irqFlags1, irqFlags2, RF_IRQFLAGS2_PAYLOADREADY)
        if self._mode == RF69_MODE_TX and (irqFlags2 & RF_IRQFLAGS2_PACKETSENT !=0):
            self._packetSentIrq = True # let _sendFrame know transmit is done
            return
        if (self._mode == RF69_MODE_RX and (irqFlags2 & RF_IRQFLAGS2_PAYLOADREADY)):
            self._setMode(RF69_MODE_STANDBY)
            self._select()
            self.spi.write(bytearray([REG_FIFO & 0x7f]))
            self.PAYLOADLEN = self.spi.read(1)[0]
            self.PAYLOADLEN = 66 if self.PAYLOADLEN > 66 else self.PAYLOADLEN
            self.TARGETID = self.spi.read(1)[0]
            # match this node's address, or broadcast address or anything in promiscuous mode
            # address situation could receive packets that are malformed and don't fit this libraries extra fields
            if(not(self._promiscuousMode or self.TARGETID==self._address or self.TARGETID==RF69_BROADCAST_ADDR)
                   or self.PAYLOADLEN < 3):
                self.PAYLOADLEN = 0
                self._unselect()
                self._receiveBegin()
                return
            
            self.DATALEN = self.PAYLOADLEN - 3
            self.SENDERID = self.spi.read(1)[0]
            CTLbyte = self.spi.read(1)[0]
            
            self.ACK_RECEIVED = CTLbyte & 0x80 #extract ACK-requested flag
            self.ACK_REQUESTED = CTLbyte & 0x40 #extract ACK-received flag
            #print(self.DATALEN, self.ACK_RECEIVED)
            
            self.DATA = self.spi.read(self.DATALEN)
            self._unselect()
            self._setMode(RF69_MODE_RX)
            self.RSSI = self.readRSSI()

    def _noInterrupts(self):
        pass

    def _interrupts(self):
        pass

    def _receiveBegin(self):
        self.DATALEN = 0
        self.SENDERID = 0
        self.TARGETID = 0
        self.PAYLOADLEN = 0
        self.ACK_REQUESTED = 0
        self.ACK_RECEIVED = 0
        self.RSSI = 0
        if (self._readReg(REG_IRQFLAGS2) & RF_IRQFLAGS2_PAYLOADREADY):
            # avoid RX deadlocks, but does this throw away an ack?
            self._writeReg(REG_PACKETCONFIG2, (self._readReg(REG_PACKETCONFIG2) & 0xFB) | RF_PACKET2_RXRESTART)
        #set DIO0 to "PAYLOADREADY" in receive mode
        self._writeReg(REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_01) 
        self._setMode(RF69_MODE_RX)

    def initialize(self, freqBand, nodeId, networkID):
        self._address = nodeId
        config = [
            [ REG_OPMODE, RF_OPMODE_SEQUENCER_ON | RF_OPMODE_LISTEN_OFF | RF_OPMODE_STANDBY ],
            [ REG_DATAMODUL, RF_DATAMODUL_DATAMODE_PACKET | RF_DATAMODUL_MODULATIONTYPE_FSK | RF_DATAMODUL_MODULATIONSHAPING_00 ], #no shaping
            [ REG_BITRATEMSB, RF_BITRATEMSB_55555], #default:4.8 KBPS
            [ REG_BITRATELSB, RF_BITRATELSB_55555],
            [ REG_FDEVMSB, RF_FDEVMSB_50000], #default:5khz, (FDEV + BitRate/2 <= 500Khz)
            [ REG_FDEVLSB, RF_FDEVLSB_50000],
            [ REG_FRFMSB, RF_FRFMSB_315 if freqBand == RF69_315MHZ else (RF_FRFMSB_433 if freqBand == RF69_433MHZ else (RF_FRFMSB_868 if freqBand == RF69_868MHZ else RF_FRFMSB_915)) ],
            [ REG_FRFMID, RF_FRFMID_315 if freqBand == RF69_315MHZ else (RF_FRFMID_433 if freqBand == RF69_433MHZ else (RF_FRFMID_868 if freqBand == RF69_868MHZ else RF_FRFMID_915)) ],
            [ REG_FRFLSB, RF_FRFLSB_315 if freqBand == RF69_315MHZ else (RF_FRFLSB_433 if freqBand == RF69_433MHZ else (RF_FRFLSB_868 if freqBand == RF69_868MHZ else RF_FRFLSB_915)) ],
            
            # looks like PA1 and PA2 are not implemented on RFM69W, hence the max output power is 13dBm
            # +17dBm and +20dBm are possible on RFM69HW
            # +13dBm formula: Pout=-18+OutputPower (with PA0 or PA1**)
            # +17dBm formula: Pout=-14+OutputPower (with PA1 and PA2)**
            # +20dBm formula: Pout=-11+OutputPower (with PA1 and PA2)** and high power PA settings (section 3.3.7 in datasheet)
            #[ REG_PALEVEL, RF_PALEVEL_PA0_ON | RF_PALEVEL_PA1_OFF | RF_PALEVEL_PA2_OFF | RF_PALEVEL_OUTPUTPOWER_11111],
            #[ REG_OCP, RF_OCP_ON | RF_OCP_TRIM_95 ], #over current protection (default is 95mA)
            
            # RXBW defaults are [ REG_RXBW, RF_RXBW_DCCFREQ_010 | RF_RXBW_MANT_24 | RF_RXBW_EXP_5] (RxBw: 10.4khz)
            [ REG_RXBW, RF_RXBW_DCCFREQ_010 | RF_RXBW_MANT_16 | RF_RXBW_EXP_2 ], #(BitRate < 2 * RxBw)
            # for BR-19200: #* 0x19 */ [ REG_RXBW, RF_RXBW_DCCFREQ_010 | RF_RXBW_MANT_24 | RF_RXBW_EXP_3 ],
            [ REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_01 ], #DIO0 is the only IRQ we're using
            [ REG_RSSITHRESH, 220 ], #must be set to dBm = (-Sensitivity / 2) - default is 0xE4=228 so -114dBm
            #[ REG_PREAMBLELSB, RF_PREAMBLESIZE_LSB_VALUE ] # default 3 preamble bytes 0xAAAAAA
            [ REG_SYNCCONFIG, RF_SYNC_ON | RF_SYNC_FIFOFILL_AUTO | RF_SYNC_SIZE_2 | RF_SYNC_TOL_0 ],
            [ REG_SYNCVALUE1, 0x2D ],     #attempt to make this compatible with sync1 byte of RFM12B lib
            [ REG_SYNCVALUE2, networkID ], #NETWORK ID
            [ REG_PACKETCONFIG1, RF_PACKET1_FORMAT_VARIABLE | RF_PACKET1_DCFREE_OFF | RF_PACKET1_CRC_ON | RF_PACKET1_CRCAUTOCLEAR_ON | RF_PACKET1_ADRSFILTERING_OFF ],
            [ REG_PAYLOADLENGTH, 66 ], #in variable length mode: the max frame size, not used in TX
            #[ REG_NODEADRS, nodeID ], #turned off because we're not using address filtering
            [ REG_FIFOTHRESH, RF_FIFOTHRESH_TXSTART_FIFONOTEMPTY | RF_FIFOTHRESH_VALUE ], #TX on FIFO not empty
            [ REG_PACKETCONFIG2, RF_PACKET2_RXRESTARTDELAY_2BITS | RF_PACKET2_AUTORXRESTART_ON | RF_PACKET2_AES_OFF ], #RXRESTARTDELAY must match transmitter PA ramp-down time (bitrate dependent)
            # for BR-19200: #* 0x3d */ [ REG_PACKETCONFIG2, RF_PACKET2_RXRESTARTDELAY_NONE | RF_PACKET2_AUTORXRESTART_ON | RF_PACKET2_AES_OFF ], #RXRESTARTDELAY must match transmitter PA ramp-down time (bitrate dependent)
            #[ REG_TESTDAGC, RF_DAGC_CONTINUOUS ], # run DAGC continuously in RX mode
            [ REG_TESTDAGC, RF_DAGC_IMPROVED_LOWBETA0 ], # run DAGC continuously in RX mode, recommended default for AfcLowBetaOn=0
            [255, 0]
        ]

        self._rstPin.value(1)
        time.sleep(.1)
        self._rstPin.value(0)
        time.sleep(.1)

        #print("attempting to sync")
        while self._readReg(REG_SYNCVALUE1) != 0xaa:
            self._writeReg(REG_SYNCVALUE1, 0xaa)
            #print("0xaa sync...")
        while self._readReg(REG_SYNCVALUE1) != 0x55:
            self._writeReg(REG_SYNCVALUE1, 0x55)
        #print("sync successful")
        
        for chunk in config:
            self._writeReg(chunk[0], chunk[1])

        self.setEncryptionKey(None)
        self.setHighPower(self._isRFM69HW)
        self._setMode(RF69_MODE_STANDBY)
        # wait for mode ready
        while (self._readReg(REG_IRQFLAGS1) & RF_IRQFLAGS1_MODEREADY) == 0x00:
            pass
        # init interrupt
        self._intPin.irq(trigger=Pin.IRQ_RISING, handler=self._interruptHandler)


    def sleep(self):
        self._setMode(RF69_MODE_SLEEP)

    def setAddress(self, addr):
        self._address = addr
        self._writeReg(REG_NODEADRS, self._address)

    def setNetwork(self, networkID):
        self._writeReg(REG_SYNCVALUE2, networkID)
    
    # set output power: 0=min, 31=max
    # this results in a "weaker" transmitted signal, and directly results in a lower RSSI at the receiver
    def setPowerLevel(self, powerLevel):
        self._powerLevel = powerLevel
        self._writeReg(REG_PALEVEL, (_readReg(REG_PALEVEL) & 0xE0) | (self._powerLevel if self._powerLevel < 31 else 31))

    def send(self, toAddress, buffer, bufferSize, requestACK):
        self._writeReg(REG_PACKETCONFIG2, (self._readReg(REG_PACKETCONFIG2) & 0xFB) | RF_PACKET2_RXRESTART) # avoid RX deadlocks
        now = self._millis()
        while (not self._canSend() and self._millis()-now < RF69_CSMA_LIMIT_MS):
            self.receiveDone()
        self._sendFrame(toAddress, buffer, bufferSize, requestACK, False)
    
    # to increase the chance of getting a packet across, call this function instead of send
    # and it handles all the ACK requesting/retrying for you :)
    # The only twist is that you have to manually listen to ACK requests on the other side and send back the ACKs
    # The reason for the semi-automaton is that the lib is ingterrupt driven and
    # requires user action to read the received data and decide what to do with it
    # replies usually take only 5-8ms at 50kbps@915Mhz
    def sendWithRetry(self, toAddress, buffer, bufferSize, retries=2, retryWaitTime=40):
        for i in range(0, retries):
            self.send(toAddress, buffer, bufferSize, True)
            sentTime = self._millis()
            while self._millis()-sentTime<retryWaitTime:
                if self.ACKReceived(toAddress):
                    return True
        return False
    
    # Should be polled immediately after sending a packet with ACK request
    def ACKReceived(self, fromNodeID):
        if self.receiveDone():
            if ((self.SENDERID == fromNodeID or fromNodeID == RF69_BROADCAST_ADDR)
                    and (self.ACK_RECEIVED != 0)):
                return True
        return False

    #check whether an ACK was requested in the last received packet (non-broadcasted packet)
    def ACKRequested(self):
        return (self.ACK_REQUESTED and (self.TARGETID != RF69_BROADCAST_ADDR)) != 0

    # Should be called immediately after reception in case sender wants ACK
    def sendACK(self, buffer="", bufferSize=0):
        sender = self.SENDERID
        _RSSI = self.RSSI #save payload received RSSI value
        self._writeReg(REG_PACKETCONFIG2, (self._readReg(REG_PACKETCONFIG2) & 0xFB) | RF_PACKET2_RXRESTART) # avoid RX deadlocks
        now = self._millis()
        while not self._canSend():
            self.receiveDone()
        self._sendFrame(sender, buffer, bufferSize, False, True)
        self.RSSI = _RSSI #restore payload RSSI
    
    def receiveDone(self):
        if (self._mode == RF69_MODE_RX  or self._mode == RF69_MODE_STANDBY) and (self.PAYLOADLEN > 0):
            self._setMode(RF69_MODE_STANDBY) #enables interrupts>
            return True
        if (self._readReg(REG_IRQFLAGS1) & RF_IRQFLAGS1_TIMEOUT) != 0:
            # https://github.com/russss/rfm69-python/blob/master/rfm69/rfm69.py#L112
            # Russss figured out that if you leave alone long enough it times out
            # tell it to stop being silly and listen for more packets
            self._writeReg(REG_PACKETCONFIG2, (self._readReg(REG_PACKETCONFIG2) & 0xFB) | RF_PACKET2_RXRESTART)
        elif self._mode == RF69_MODE_RX:
            # already in RX no payload yet
            return False
        self._receiveBegin()
        return False
    
    # To enable encryption: radio.encrypt("ABCDEFGHIJKLMNOP")
    # To disable encryption: radio.encrypt(null)
    # KEY HAS TO BE 16 bytes !!!
    def setEncryptionKey(self, key):
        if key is not None:
            if len(key) != 16:
                raise Exception("Key must be exactly 16 bytes!")
            self._setMode(RF69_MODE_STANDBY)
            keyBytes = []
            self._select()
            self.spi.write(bytearray([REG_AESKEY1 | 0x80]))
            for i in range(0,16):
                keyBytes.append(ord(key[i]))
                self.spi.write(keyBytes)
            self._unselect()
            self._writeReg(REG_PACKETCONFIG2, (self._readReg(REG_PACKETCONFIG2) & 0xFE) | (0 if key is None else 1))

    # The following methods are not required by BaseRadio.
    # They depend too heavily on the specific radio hardware and would not get any benefit from being part of the
    # BaseRadio class.
    
    def readRSSI(self, forceTrigger=False):
        rssi = 0
        if (forceTrigger):
            # RSSI trigger not needed if DAGC is in continuous mode
            self._writeReg(REG_RSSICONFIG, RF_RSSI_START)
            while ((self._readReg(REG_RSSICONFIG) & RF_RSSI_DONE) == 0x00):
                pass # Wait for RSSI_Ready
        rssi = -self._readReg(REG_RSSIVALUE)
        rssi >>= 1
        return rssi

    # ON  = disable filtering to capture all frames on network
    # OFF = enable node+broadcast filtering to capture only frames sent to this/broadcast address
    def setPromiscuous(self, onOff):
        self._promiscuousMode = onOff
        
    def setHighPower(self, onOff):
        self._isRFM69HW = onOff
        self._writeReg(REG_OCP, RF_OCP_OFF if self._isRFM69HW else RF_OCP_ON)
        if (self._isRFM69HW):
            # enable P1 & P2 amplifier stages
            self._writeReg(REG_PALEVEL, (self._readReg(REG_PALEVEL) & 0x1F) | RF_PALEVEL_PA1_ON | RF_PALEVEL_PA2_ON) 
        else:
            # enable P0 only
            self._writeReg(REG_PALEVEL, RF_PALEVEL_PA0_ON | RF_PALEVEL_PA1_OFF | RF_PALEVEL_PA2_OFF | self.powerLevel) 

    def setHighPowerRegs(self, onOff):
        self._writeReg(REG_TESTPA1, 0x5D if onOff else 0x55)
        self._writeReg(REG_TESTPA2, 0x7C if onOff else 0x70)

    """
    def readAllRegs(self):
    print "Register, Address, Value"
    print "REG_FIFO, 0x00, {}".format(hex(self._readReg(REG_FIFO)))
    print "REG_OPMODE, 0x01, {}".format(hex(self._readReg(REG_OPMODE)))
    print "REG_DATAMODUL, 0x02, {}".format(hex(self._readReg(REG_DATAMODUL)))
    print "REG_BITRATEMSB, 0x03, {}".format(hex(self._readReg(REG_BITRATEMSB)))
    print "REG_BITRATELSB, 0x04, {}".format(hex(self._readReg(REG_BITRATELSB)))
    print "REG_FDEVMSB, 0x05, {}".format(hex(self._readReg(REG_FDEVMSB)))
    print "REG_FDEVLSB, 0x06, {}".format(hex(self._readReg(REG_FDEVLSB)))
    print "REG_FRFMSB, 0x07, {}".format(hex(self._readReg(REG_FRFMSB)))
    print "REG_FRFMID, 0x08, {}".format(hex(self._readReg(REG_FRFMID)))
    print "REG_FRFLSB, 0x09, {}".format(hex(self._readReg(REG_FRFLSB)))
    print "REG_OSC1, 0x0A, {}".format(hex(self._readReg(REG_OSC1)))
    print "REG_AFCCTRL, 0x0B, {}".format(hex(self._readReg(REG_AFCCTRL)))
    print "REG_LOWBAT, 0x0C, {}".format(hex(self._readReg(REG_LOWBAT)))
    print "REG_LISTEN1, 0x0D, {}".format(hex(self._readReg(REG_LISTEN1)))
    print "REG_LISTEN2, 0x0E, {}".format(hex(self._readReg(REG_LISTEN2)))
    print "REG_LISTEN3, 0x0F, {}".format(hex(self._readReg(REG_LISTEN3)))
    print "REG_VERSION, 0x10, {}".format(hex(self._readReg(REG_VERSION)))
    print "REG_PALEVEL, 0x11, {}".format(hex(self._readReg(REG_PALEVEL)))
    print "REG_PARAMP, 0x12, {}".format(hex(self._readReg(REG_PARAMP)))
    print "REG_OCP, 0x13, {}".format(hex(self._readReg(REG_OCP)))
    print "REG_AGCREF, 0x14, {}".format(hex(self._readReg(REG_AGCREF)))
    print "REG_AGCTHRESH1, 0x15, {}".format(hex(self._readReg(REG_AGCTHRESH1)))
    print "REG_AGCTHRESH2, 0x16, {}".format(hex(self._readReg(REG_AGCTHRESH2)))
    print "REG_AGCTHRESH3, 0x17, {}".format(hex(self._readReg(REG_AGCTHRESH3)))
    print "REG_LNA, 0x18, {}".format(hex(self._readReg(REG_LNA)))
    print "REG_RXBW, 0x19, {}".format(hex(self._readReg(REG_RXBW)))
    print "REG_AFCBW, 0x1A, {}".format(hex(self._readReg(REG_AFCBW)))
    print "REG_OOKPEAK, 0x1B, {}".format(hex(self._readReg(REG_OOKPEAK)))
    print "REG_OOKAVG, 0x1C, {}".format(hex(self._readReg(REG_OOKAVG)))
    print "REG_OOKFIX, 0x1D, {}".format(hex(self._readReg(REG_OOKFIX)))
    print "REG_AFCFEI, 0x1E, {}".format(hex(self._readReg(REG_AFCFEI)))
    print "REG_AFCMSB, 0x1F, {}".format(hex(self._readReg(REG_AFCMSB)))
    print "REG_AFCLSB, 0x20, {}".format(hex(self._readReg(REG_AFCLSB)))
    print "REG_FEIMSB, 0x21, {}".format(hex(self._readReg(REG_FEIMSB)))
    print "REG_FEILSB, 0x22, {}".format(hex(self._readReg(REG_FEILSB)))
    print "REG_RSSICONFIG, 0x23, {}".format(hex(self._readReg(REG_RSSICONFIG)))
    print "REG_RSSIVALUE, 0x24, {}".format(hex(self._readReg(REG_RSSIVALUE)))
    print "REG_DIOMAPPING1, 0x25, {}".format(hex(self._readReg(REG_DIOMAPPING1)))
    print "REG_DIOMAPPING2, 0x26, {}".format(hex(self._readReg(REG_DIOMAPPING2)))
    print "REG_IRQFLAGS1, 0x27, {}".format(hex(self._readReg(REG_IRQFLAGS1)))
    print "REG_IRQFLAGS2, 0x28, {}".format(hex(self._readReg(REG_IRQFLAGS2)))
    print "REG_RSSITHRESH, 0x29, {}".format(hex(self._readReg(REG_RSSITHRESH)))
    print "REG_RXTIMEOUT1, 0x2A, {}".format(hex(self._readReg(REG_RXTIMEOUT1)))
    print "REG_RXTIMEOUT2, 0x2B, {}".format(hex(self._readReg(REG_RXTIMEOUT2)))
    print "REG_PREAMBLEMSB, 0x2C, {}".format(hex(self._readReg(REG_PREAMBLEMSB)))
    print "REG_PREAMBLELSB, 0x2D, {}".format(hex(self._readReg(REG_PREAMBLELSB)))
    print "REG_SYNCCONFIG, 0x2E, {}".format(hex(self._readReg(REG_SYNCCONFIG)))
    print "REG_SYNCVALUE1, 0x2F, {}".format(hex(self._readReg(REG_SYNCVALUE1)))
    print "REG_SYNCVALUE2, 0x30, {}".format(hex(self._readReg(REG_SYNCVALUE2)))
    print "REG_SYNCVALUE3, 0x31, {}".format(hex(self._readReg(REG_SYNCVALUE3)))
    print "REG_SYNCVALUE4, 0x32, {}".format(hex(self._readReg(REG_SYNCVALUE4)))
    print "REG_SYNCVALUE5, 0x33, {}".format(hex(self._readReg(REG_SYNCVALUE5)))
    print "REG_SYNCVALUE6, 0x34, {}".format(hex(self._readReg(REG_SYNCVALUE6)))
    print "REG_SYNCVALUE7, 0x35, {}".format(hex(self._readReg(REG_SYNCVALUE7)))
    print "REG_SYNCVALUE8, 0x36, {}".format(hex(self._readReg(REG_SYNCVALUE8)))
    print "REG_PACKETCONFIG1, 0x37, {}".format(hex(self._readReg(REG_PACKETCONFIG1)))
    print "REG_PAYLOADLENGTH, 0x38, {}".format(hex(self._readReg(REG_PAYLOADLENGTH)))
    print "REG_NODEADRS, 0x39, {}".format(hex(self._readReg(REG_NODEADRS)))
    print "REG_BROADCASTADRS, 0x3A, {}".format(hex(self._readReg(REG_BROADCASTADRS)))
    print "REG_AUTOMODES, 0x3B, {}".format(hex(self._readReg(REG_AUTOMODES)))
    print "REG_FIFOTHRESH, 0x3C, {}".format(hex(self._readReg(REG_FIFOTHRESH)))
    print "REG_PACKETCONFIG2, 0x3D, {}".format(hex(self._readReg(REG_PACKETCONFIG2)))
    print "REG_AESKEY1, 0x3E, {}".format(hex(self._readReg(REG_AESKEY1)))
    print "REG_AESKEY2, 0x3F, {}".format(hex(self._readReg(REG_AESKEY2)))
    print "REG_AESKEY3, 0x40, {}".format(hex(self._readReg(REG_AESKEY3)))
    print "REG_AESKEY4, 0x41, {}".format(hex(self._readReg(REG_AESKEY4)))
    print "REG_AESKEY5, 0x42, {}".format(hex(self._readReg(REG_AESKEY5)))
    print "REG_AESKEY6, 0x43, {}".format(hex(self._readReg(REG_AESKEY6)))
    print "REG_AESKEY7, 0x44, {}".format(hex(self._readReg(REG_AESKEY7)))
    print "REG_AESKEY8, 0x45, {}".format(hex(self._readReg(REG_AESKEY8)))
    print "REG_AESKEY9, 0x46, {}".format(hex(self._readReg(REG_AESKEY9)))
    print "REG_AESKEY10, 0x47, {}".format(hex(self._readReg(REG_AESKEY10)))
    print "REG_AESKEY11, 0x48, {}".format(hex(self._readReg(REG_AESKEY11)))
    print "REG_AESKEY12, 0x49, {}".format(hex(self._readReg(REG_AESKEY12)))
    print "REG_AESKEY13, 0x4A, {}".format(hex(self._readReg(REG_AESKEY13)))
    print "REG_AESKEY14, 0x4B, {}".format(hex(self._readReg(REG_AESKEY14)))
    print "REG_AESKEY15, 0x4C, {}".format(hex(self._readReg(REG_AESKEY15)))
    print "REG_AESKEY16, 0x4D, {}".format(hex(self._readReg(REG_AESKEY16)))
    print "REG_TEMP1, 0x4E, {}".format(hex(self._readReg(REG_TEMP1)))
    print "REG_TEMP2, 0x4F, {}".format(hex(self._readReg(REG_TEMP2)))
    if self._isRFM69HW:
        print "REG_TESTPA1, 0x5A, {}".format(hex(self._readReg(REG_TESTPA1)))
        print "REG_TESTPA2, 0x5C, {}".format(hex(self._readReg(REG_TESTPA2)))
    print "REG_TESTDAGC, 0x6F, {}".format(hex(self._readReg(REG_TESTDAGC)))
    """
    # returns centigrade
    def readTemperature(self, calFactor):  
        self._setMode(RF69_MODE_STANDBY)
        self._writeReg(REG_TEMP1, RF_TEMP1_MEAS_START)
        while ((self._readReg(REG_TEMP1) & RF_TEMP1_MEAS_RUNNING)):
            pass
        #'complement'corrects the slope, rising temp = rising val
        # COURSE_TEMP_COEF puts reading in the ballpark, user can add additional correction
        return ~self._readReg(REG_TEMP2) + COURSE_TEMP_COEF + calFactor 

    def rcCalibration(self):
        _writeReg(REG_OSC1, RF_OSC1_RCCAL_START)
        while ((_readReg(REG_OSC1) & RF_OSC1_RCCAL_DONE) == 0x00):
            pass
