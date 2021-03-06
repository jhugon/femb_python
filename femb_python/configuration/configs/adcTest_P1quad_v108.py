#!/usr/bin/env python33

"""
Configuration for P1 ADC quad-chip board. Note that the fourth socket doesn't
have full external clock functionality because the FPGA ran out of PLLs.
"""

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from builtins import super
from builtins import int
from builtins import range
from builtins import hex
from builtins import str
from future import standard_library
standard_library.install_aliases()
from builtins import object
import sys 
import string
import time
import copy
import os.path
import pprint
import subprocess
from femb_python.femb_udp import FEMB_UDP
from femb_python.configuration.config_base import FEMB_CONFIG_BASE, FEMBConfigError, SyncADCError, InitBoardError, ConfigADCError, ReadRegError
from femb_python.configuration.adc_asic_reg_mapping_P1_singleADC import ADC_ASIC_REG_MAPPING

class FEMB_CONFIG(FEMB_CONFIG_BASE):

    def __init__(self,exitOnError=False):
        super().__init__(exitOnError=exitOnError)
        #declare board specific registers
        self.FEMB_VER = "adctestP1quad"

        self.REG_RESET = 0 # bit 0 system, 1 reg, 2 alg, 3 udp
        self.REG_PWR_CTRL = 1  # bit 0-3 pwr, 8-15 blue LEDs near buttons
        self.REG_ASIC_SPIPROG_RESET = 2 # bit 0 FE SPI, 1 ADC SPI, 4 FE ASIC RESET, 5 ADC ASIC RESET, 6 SOFT ADC RESET & SPI readback check
        self.REG_SEL_CH = 3 # bit 0-7 chip, 8-15 channel, 31 WIB mode

        self.REG_DAC1 = 4 # bit 0-15 DAC val, 16-19 tp mode select, 31 set dac
        self.REG_DAC2 = 5 # bit 0-15 tp period, 16-31 tp shift

        self.REG_FPGA_TST_PATT = 6 # bit 0-11 tst patt, 16 enable

        self.REG_ADC_CLK = 7 # bit 0-7 clk phase, 8 clk speed sel
        self.REG_LATCHLOC = 8 # bit 0-7 ADC1, 8-15 ADC2, 16-23 ADC3, 24-31 ADC4

        self.REG_STOP_ADC = 9 # bit 0 stops sending convert, read ADC HEADER redundant with reg 2

        self.REG_UDP_FRAME_SIZE = 63 # bits 0-11
        self.REG_FIRMWARE_VERSION = 0xFF # 255 in decimal
        self.CONFIG_FIRMWARE_VERSION = 0x108 # this file is written for this
        
        #self.REG_LATCHLOC_data_2MHz = 0x6060606
        self.REG_LATCHLOC_data_2MHz = 0x6060605
        self.REG_LATCHLOC_data_1MHz = 0x4040404

        self.REG_LATCHLOC_data_2MHz_cold = 0x5050505
        self.REG_LATCHLOC_data_1MHz_cold = 0x4040404

        #self.REG_CLKPHASE_data_2MHz = 0x09
        self.REG_CLKPHASE_data_2MHz = 0xa
        #self.REG_CLKPHASE_data_1MHz = 0x140
        self.REG_CLKPHASE_data_1MHz = 0x168

        self.REG_CLKPHASE_data_2MHz_cold = 0x90
        self.REG_CLKPHASE_data_1MHz_cold = 0x140

        self.REG_HDR_ERROR_RESET = 47
        self.REG_CONV_ERROR_BASES = [48,50,52,54] # for each chip
        self.REG_HDR_ERROR_BASES = [49,51,53,55] # for each chip

        self.DEFAULT_FPGA_TST_PATTERN = 0x12
        self.ADC_TESTPATTERN = [0x12, 0x345, 0x678, 0xf1f, 0xad, 0xc01, 0x234, 0x567, 0x89d, 0xeca, 0xff0, 0x123, 0x456, 0x789, 0xabc, 0xdef]

        # registers 64-88 are SPI to ASICs
        # 88 is last register besides 255 which is firmware version
        self.REG_FESPI_BASE = 84 # this configures all FE ASICs
        #self.REG_ADCSPI_BASES = [0x40,0x40,0x40,0x40] # for each chip
        self.REG_ADCSPI_BASES = [64,69,74,79]

        self.REG_EXTCLK_INV = 10
        self.REG_EXTCLK_BASES = [11,20,29,38] # for each chip
        self.FPGA_FREQ_MHZ = 200 # frequency of FPGA clock in MHz

        self.REG_PLL_BASES = [17,26,35,44] # for each chip

        self.NASICS = 4
        self.F2DEFAULT = 0
        self.CLKDEFAULT = "fifo"

        self.isExternalClock = True #False = internal monostable, True = external
        self.is1MHzSAMPLERATE = False #True = 1MHz, False = 2MHz
        self.COLD = False
        self.enableTest = 0
        self.doSpiWrite = True
        self.doReSync = True
        self.scanSyncSettings = True
        self.adcSyncStatus = False
        self.maxSyncAttempts = 10
        self.numSyncTests = 25

        #initialize FEMB UDP object
        self.femb = FEMB_UDP()

        #list of adc configuration register mappings
        self.adc_regs = ADC_ASIC_REG_MAPPING()

    def printParameters(self):
        print("External ADC Clocks    \t",self.isExternalClock)
        print("Cryogenic temperature  \t",self.COLD)
        print("Enable ADC test input  \t",self.enableTest)
        print("Enable SPI writing     \t",self.doSpiWrite)
        print("MAX SYNC ATTEMPTS      \t",self.maxSyncAttempts)
        print("Do resync              \t",self.doReSync)
        print("Try all sync settings  \t",self.scanSyncSettings)
        print("1MHz Sampling          \t",self.is1MHzSAMPLERATE)
        print("SYNC STATUS            \t",self.adcSyncStatus)

    def resetBoard(self):
        """
        Reset registers and state machines NOT udp
        Make sure to set reg 0 back to zero
            or there will be much sadness!
        """
        #Reset registers
        self.femb.write_reg( self.REG_RESET, 2)
        time.sleep(1.)

        #Reset state machines
        self.femb.write_reg( self.REG_RESET, 4)
        time.sleep(1.)

        #Reset reset register to 0
        self.femb.write_reg( self.REG_RESET, 0)
        time.sleep(0.2)

    def initBoard(self):
        # test readback
        readback = self.femb.read_reg(self.REG_FIRMWARE_VERSION)
        if readback is None:
           print("FEMB_CONFIG: Error reading register 0, Exiting.")
           return False
        if readback is False:
            if self.exitOnError:
                print("FEMB_CONFIG: Error reading register 0, Exiting.")
                sys.exit(1)
            else:
                raise ReadRegError("Couldn't read register 0")
                return False

        ##### Start Top-level Labview stacked sequence struct 0
        firmwareVersion = self.femb.read_reg(self.REG_FIRMWARE_VERSION) & 0xFFFF
        if firmwareVersion == None:
            print("FEMB_CONFIG: Error reading register 0, Exiting.")
            return False
        if firmwareVersion != self.CONFIG_FIRMWARE_VERSION:
            raise FEMBConfigError("Board firmware version {} doesn't match configuration firmware version {}".format(firmwareVersion, self.CONFIG_FIRMWARE_VERSION))
            return False
        print("Firmware Version: ",firmwareVersion)

        self.femb.write_reg(self.REG_UDP_FRAME_SIZE,0x1FB)
        time.sleep(0.05)
        self.setFPGADac(0,0,0,0) # write regs 4 and 5
        #self.femb.write_reg(1,0) # pwr ctrl --disabled BK
        self.femb.write_reg(3, (5 << 8 )) # chn sel
        self.femb.write_reg(6,self.DEFAULT_FPGA_TST_PATTERN)  #tst pattern
        self.femb.write_reg(7,13)  #adc clk
        self.femb.write_reg(8,0)  #latchloc
        ##### End Top-level Labview stacked sequence struct 0

        #Set FPGA test pattern register
        self.femb.write_reg(self.REG_FPGA_TST_PATT, self.DEFAULT_FPGA_TST_PATTERN) # test pattern off
        #self.femb.write_reg(self.REG_FPGA_TST_PATT, self.DEFAULT_FPGA_TST_PATTERN+(1 << 16)) # test pattern on

        #Set ADC latch_loc and clock phase and sample rate
        if self.is1MHzSAMPLERATE == True:
            if self.COLD:
                self.femb.write_reg( self.REG_LATCHLOC, self.REG_LATCHLOC_data_1MHz_cold)
                self.femb.write_reg( self.REG_ADC_CLK, (self.REG_CLKPHASE_data_1MHz_cold & 0xFF) | (1 << 8))
            else:
                self.femb.write_reg( self.REG_LATCHLOC, self.REG_LATCHLOC_data_1MHz)
                self.femb.write_reg( self.REG_ADC_CLK, (self.REG_CLKPHASE_data_1MHz & 0xFF) | (1 << 8))
        else: # use 2 MHz values
            if self.COLD:
                self.femb.write_reg( self.REG_LATCHLOC, self.REG_LATCHLOC_data_2MHz_cold)
                self.femb.write_reg( self.REG_ADC_CLK, (self.REG_CLKPHASE_data_2MHz_cold & 0xFF))
            else:
                self.femb.write_reg( self.REG_LATCHLOC, self.REG_LATCHLOC_data_2MHz)
                self.femb.write_reg( self.REG_ADC_CLK, (self.REG_CLKPHASE_data_2MHz & 0xFF))

        #specify wib data format mode
        self.femb.write_reg_bits( self.REG_SEL_CH,31,1,1)

        #turn ON ASICs when initializing board
        self.turnOnAsics()

        #turn OFF ASICs when initializing board
        #self.turnOffAsics()

        #test only, leave EXT TP mode ON
        #self.setFPGADac(0,1,0,0) # write regs 4 and 5
        return True

    def initAsic(self, asicNum=None):
        if asicNum == None :
            print("FEMB_CONFIG: Invalid ASIC # defined, will not initialize ASIC.")
            return False
        asicNumVal = int(asicNum)
        if (asicNumVal < 0)  or (asicNumVal >= self.NASICS ):
            print("FEMB_CONFIG: Invalid ASIC # defined, will not initialize ASIC.")
            return False

        #turn on ASIC
        #self.turnOnAsic(asicNumVal)

        #Reset ASICs
        self.femb.write_reg( self.REG_ASIC_SPIPROG_RESET, 0x0) # zero out reg
        self.femb.write_reg( self.REG_ASIC_SPIPROG_RESET, 0x30) # reset FE and ADC
        self.femb.write_reg( self.REG_ASIC_SPIPROG_RESET, 0x0) # zero out reg
        time.sleep(1.)

        #write external clock specific registers
        self.setExtClockRegs(asicNumVal)

        #specify ASIC for streaming data output
        self.selectAsic(asicNumVal)

        #Configure ADC ASIC registers (and external clock inside)
        if self.isExternalClock == True :
           self.configAdcAsic(asicNum=asicNumVal, testInput=self.enableTest, clockExternal=True)
        else :
           self.configAdcAsic(asicNum=asicNumVal, testInput=self.enableTest, clockMonostable=True)

        #acutally program the ADC using the default parameters
        self.doAdcAsicConfig(asicNumVal)
        self.setExtClockRegs(asicNumVal)
        self.selectAsic(asicNumVal)
        self.checkAdcErrorCount(asicNumVal)
        #self.doAdcAsicConfig(asicNumVal)

        #if sync fails, optionally attempt to try all other parameters to achieve sync
        if (self.adcSyncStatus == False) and (self.scanSyncSettings == True):
            self.fixUnsync(asicNumVal)

        #check SPI + SYNC status here
        syncStatus = self.getSyncStatus()
        if syncStatus == None :
            print("FEMB_CONFIG: ASIC initialization failed")
            return False
        adcSpi = syncStatus[1][asicNumVal]
        if adcSpi == False:
            print("FEMB_CONFIG: ADC ASIC SPI readback failed")
            return False

        #check sync here
        #self.printSyncRegister()
        self.checkAdcErrorCount(asicNumVal)
        print("SYNC STATUS:\t",self.adcSyncStatus)
        if self.adcSyncStatus == False :
            print("FEMB_CONFIG: ASIC NOT SYNCHRONIZED")
            return False
        return True

    def configAdcAsic(self,asicNum=None,enableOffsetCurrent=None,offsetCurrent=None,testInput=None,
                            freqInternal=None,sleep=None,pdsr=None,pcsr=None,
                            clockMonostable=None,clockExternal=None,clockFromFIFO=None,
                            sLSB=None,f0=None,f1=None,f2=None,f3=None,f4=None,f5=None):
        """
        Configure ADCs
          enableOffsetCurrent: 0 disable offset current, 1 enable offset current
          offsetCurrent: 0-15, amount of current to draw from sample and hold
          testInput: 0 digitize normal input, 1 digitize test input
          freqInternal: internal clock frequency: 0 1MHz, 1 2MHz
          sleep: 0 disable sleep mode, 1 enable sleep mode
          pdsr: if pcsr=0: 0 PD is low, 1 PD is high
          pcsr: 0 power down controlled by pdsr, 1 power down controlled externally
          Only one of these can be enabled:
            clockMonostable: True ADC uses monostable clock
            clockExternal: True ADC uses external clock
            clockFromFIFO: True ADC uses digital generator FIFO clock
          sLSB: LSB current steering mode. 0 for full, 1 for partial (ADC7 P1)
          f0, f1, f2, f3, f4, f5: version specific
        """
        if asicNum == None :
            return None
        asicNumVal = int(asicNum)
        if (asicNumVal < 0)  or (asicNumVal >= self.NASICS ):
            return None

        #check requested clocks
        if clockMonostable and clockExternal:
            return None
        if clockMonostable and clockFromFIFO:
            return None
        if clockExternal and clockFromFIFO:
            return None

        if enableOffsetCurrent is None:
            enableOffsetCurrent=0
        if offsetCurrent is None:
            offsetCurrent=0
        else:
            offsetCurrent = int("{:04b}".format(offsetCurrent)[::-1],2) # need to reverse bits, use string/list tricks
        if testInput is None:
            testInput=1
        if freqInternal is None:
            freqInternal=1
        if sleep is None:
            sleep=0
        if pdsr is None:
            pdsr=0
        if pcsr is None:
            pcsr=0
        if sLSB is None:
            sLSB = 0
        if f1 is None:
            f1 = 0
        if f2 is None:
            f2 = 0
        if f3 is None:
            f3 = 0
        if f4 is None:
            f4 = 1
        if f5 is None:
            f5 = 0
        if not (clockMonostable or clockExternal or clockFromFIFO):
            clockExternal=True
        # a bunch of things depend on the clock choice
        clk0=0
        clk1=0
        if clockExternal:
            clk0=1
            clk1=0
        elif clockFromFIFO:
            clk0=0
            clk1=1
        if f0 is None:
            if clockExternal:
                f0 = 1
            else:
                f0 = 0
        #moved external clock reg config to init function for now
        #if clockExternal:
        #    self.extClock(enable=True)
        #else:
        #    self.extClock(enable=False)

        #determine register values for requested config
        self.adc_regs.set_chip(en_gr=enableOffsetCurrent,d=offsetCurrent,tstin=testInput,frqc=freqInternal,slp=sleep,pdsr=pdsr,pcsr=pcsr,clk0=clk0,clk1=clk1,f0=f0,f1=f1,f2=f2,f3=f3,f4=f4,f5=f5,slsb=sLSB)

        #write config registers
        self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET,0)
        for iReg in range(0,5,1):
            self.femb.write_reg(self.REG_ADCSPI_BASES[asicNumVal]+iReg, self.adc_regs.REGS[iReg])
            #print("{:3}  {:#010x}".format(self.REG_ADCSPI_BASES[iChip]+iReg, chipRegs[iReg]))

    #function programs ADC SPI and does multiple tests to ensure sync is good, note uses recursion
    def doAdcAsicConfig(self,asicNum=None, syncAttempt=0):
        if asicNum == None :
            return None
        asicNumVal = int(asicNum)
        if (asicNumVal < 0)  or (asicNumVal >= self.NASICS ):
            return None

        #write ADC ASIC SPI, do on intial sync attempt ONLY
        #if (self.doSpiWrite == True) and (syncAttempt == 0):
        if True :
            print("Program ADC ASIC SPI")
            #self.REG_ASIC_SPIPROG_RESET = 2 # bit 0 FE SPI, 1 ADC SPI, 4 FE ASIC RESET, 5 ADC ASIC RESET, 6 SOFT ADC RESET & SPI readback check
            self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET, 0x0)
            self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET, 0x40) #SOFT ADC reset
            time.sleep(0.01)
            self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET, 0x0)
            self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET, 0x20) #ADC reset
            time.sleep(0.01)
            self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET, 0x0)
            self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET, 0x40) #SOFT ADC reset
            time.sleep(0.01)
            self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET, 0x0)
            self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET, 0x20) #ADC reset
            time.sleep(0.01)
            self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET, 0x0)
            self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET, 0x2) #ADC SPI write
            time.sleep(0.01)
            self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET, 0x0)
            self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET, 0x2) #ADC SPI write
            time.sleep(0.01)
            self.femb.write_reg ( self.REG_ASIC_SPIPROG_RESET, 0)

        #soft reset
        #self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET,0)
        #self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET,0x40) # soft reset
        #self.femb.write_reg(self.REG_ASIC_SPIPROG_RESET,0)

        time.sleep(0.05)
        self.femb.write_reg(self.REG_HDR_ERROR_RESET,0)
        self.femb.write_reg(self.REG_HDR_ERROR_RESET,0x1) #reset counters
        self.femb.write_reg(self.REG_HDR_ERROR_RESET,0)


        #optionally check the ADC sync
        return
        if self.doReSync == False:
            return

        #self.checkAdcSyncBits(asicNumVal)
        print("RECURSION LEVEL ",syncAttempt)
        self.checkAdcErrorCount(asicNumVal)

        #try again if sync not achieved, note recursion, stops after some maximum number of attempts
        if self.adcSyncStatus == False :
            if syncAttempt >= self.maxSyncAttempts :
                print("doAsicConfig: Could not sync ADC ASIC, giving up after " + str(self.maxSyncAttempts) + " attempts.")
                return None
            else:
                self.doAdcAsicConfig(asicNumVal,syncAttempt+1)

    #check ADC sync bits several times to ensure sync is stable
    def checkAdcSyncBits(self,asicNum):
        if asicNum == None :
            return None
        asicNumVal = int(asicNum)
        if (asicNumVal < 0)  or (asicNumVal >= self.NASICS ):
            return None

        self.adcSyncStatus = False #assume sync is BAD initially
        isSync = True
        for syncTest in range(0,self.numSyncTests,1):
            regVal = self.femb.read_reg(2)
            if regVal == None:
                print("doAdcAsicConfig: Could not check SYNC status, bad")
                self.adcSyncStatus = False
                return None

            syncVal = ((regVal >> 24) & 0xFF)
            syncVal = ((syncVal >> 2*asicNumVal) & 0x3)
            if syncVal != 0x0 :
                #bad sync detected
                isSync = False
                break
        self.adcSyncStatus = isSync
  
    def checkAdcErrorCount(self,asicNum):
        if asicNum == None :
            return None
        asicNumVal = int(asicNum)
        if (asicNumVal < 0)  or (asicNumVal >= self.NASICS ):
            return None

        #check header error count
        self.adcSyncStatus = False #assume sync is BAD initially

        self.femb.write_reg(self.REG_HDR_ERROR_RESET,0)
        self.femb.write_reg(self.REG_HDR_ERROR_RESET,0x1) #reset counters
        self.femb.write_reg(self.REG_HDR_ERROR_RESET,0)

        time.sleep(0.05) #optional delay

        errRegNum = self.REG_HDR_ERROR_BASES[asicNumVal]
        errorCount = self.femb.read_reg(errRegNum)
        if errorCount == None:
            print("doAdcAsicConfig: Could not check SYNC status, bad")
            return None        

        print( "ERROR COUNT ASIC ",asicNumVal , "\tcount ",errorCount)

        if errorCount == 0:
            self.adcSyncStatus = True

    def fixUnsync(self, asicNum):
        if asicNum == None :
            return None
        asicNumVal = int(asicNum)
        if (asicNumVal < 0)  or (asicNumVal >= self.NASICS ):
            return None

        initLATCH = self.femb.read_reg ( self.REG_LATCHLOC )
        initPHASE = self.femb.read_reg ( self.REG_ADC_CLK ) # remember bit 16 sample rate
        if (initLATCH == None ) or (initPHASE == None ) :
            return None

        phases = [0,1,2,3]
        #phases = [0,1,2,3,0,3,2,1]
        if self.COLD:
            phases = [0,1,2,3,0,3,2,1]

        #loop through sync parameters
        for shift in range(4,7,1):
            shiftMask = (0xFF << 8*asicNum)
            testShift = ( (initLATCH & ~(shiftMask)) | (shift << 8*asicNum) )
            self.femb.write_reg ( self.REG_LATCHLOC, testShift )
            time.sleep(0.01)
            for phase in phases:
                clkMask = (0x3 << 2*asicNum)
                testPhase = ( (initPHASE & ~(clkMask)) | (phase << 2*asicNum) ) 
                self.femb.write_reg ( self.REG_ADC_CLK, testPhase )
                time.sleep(0.01)
                print("try shift: {} phase: {} testingUnsync...".format(hex(testShift),hex(testPhase)))
                #try ADC config with new
                isBad = 0
                for test in range(0,10,1):
                    self.doAdcAsicConfig(asicNumVal)
                    self.checkAdcErrorCount(asicNumVal)
                    if self.adcSyncStatus == False :
                        isBad = 1
                        break
                if isBad == 1:
                    continue
                if self.adcSyncStatus == True :
                    print("FEMB_CONFIG--> ADC synchronized")
                    print("FEMB_CONFIG LATCHLOC ",hex(testShift)," , PHASE " , hex(testPhase) )
                    return True
        #if program reaches here, sync has failed
        print("Error: FEMB_CONFIG--> ADC SYNC process failed for ADC # " + str(asicNumVal))
        print("Setting back to original values: LATCHLOC: {:#010x}, PHASE: {:#010x}".format(initLATCH,initPHASE & 0xF))
        self.femb.write_reg ( self.REG_LATCHLOC, initLATCH )
        self.femb.write_reg ( self.REG_ADC_CLK, initPHASE )
        self.adcSyncStatus  = False

    def getSyncStatus(self):
        syncBits = None
        adc0 = None
        fe0 = None
        adc1 = None
        fe1 = None
        adc2 = None
        fe2 = None
        adc3 = None
        fe3 = None
        reg = self.femb.read_reg(self.REG_ASIC_SPIPROG_RESET)
        if reg is None:
            print("Error: can't read back sync register")
            return None
        else:
            print("Register 2: {:#010x}".format(reg))
            syncBits = reg >> 24
            reg = reg >> 16
            adc0 = ((reg >> 0) & 1)== 1
            fe0 = ((reg >> 1) & 1)== 1
            adc1 = ((reg >> 2) & 1)== 1
            fe1 = ((reg >> 3) & 1)== 1
            adc2 = ((reg >> 4) & 1)== 1
            fe2 = ((reg >> 5) & 1)== 1
            adc3 = ((reg >> 6) & 1)== 1
            fe3 = ((reg >> 7) & 1)== 1
        return (fe0, fe1, fe2, fe3), (adc0, adc1, adc2, adc3), syncBits

    def printSyncRegister(self):
        (fe0, fe1, fe2, fe3), (adc0, adc1, adc2, adc3), syncBits = self.getSyncStatus()
        print("ASIC Readback Status:")
        print("  ADC 0:",adc0,"FE 0:",fe0)
        print("  ADC 1:",adc1,"FE 1:",fe1)
        print("  ADC 2:",adc2,"FE 2:",fe2)
        print("  ADC 3:",adc3,"FE 3:",fe3)
        print("ADC Sync Bits: {:#010b} (0 is good)".format(syncBits))

    def selectAsic(self,asic):
        """
        asic is chip number 0 to 3
        """
        asicVal = int(asic)
        if (asicVal < 0 ) or (asicVal >= self.NASICS ) :
            print( "femb_config_femb : selectChan - invalid ASIC number, only 0 to {} allowed".format(self.NASICS-1))
            return

        self.femb.write_reg( self.REG_STOP_ADC, 1)
        time.sleep(0.05)

        # in this firmware asic = 0 disables readout, so asics are 1,2,3,4
        self.femb.write_reg_bits( self.REG_SEL_CH , 0, 0x7, asicVal+1 )
        self.femb.write_reg( self.REG_STOP_ADC, 0)

        self.femb.write_reg(self.REG_HDR_ERROR_RESET,0)
        self.femb.write_reg(self.REG_HDR_ERROR_RESET,0x1) #reset counters
        self.femb.write_reg(self.REG_HDR_ERROR_RESET,0)

    def extClock(self, enable=False, 
                period=500, mult=1, 
                offset_rst=0, offset_read=480, offset_msb=230, offset_lsb=480,
                width_rst=50, width_read=20, width_msb=270, width_lsb=20,
                offset_lsb_1st_1=50, width_lsb_1st_1=190,
                offset_lsb_1st_2=480, width_lsb_1st_2=20,
                inv_rst=True, inv_read=True, inv_msb=False, inv_lsb=False, inv_lsb_1st=False):
        """
        Programs external clock. All non-boolean arguments except mult are in nanoseconds
        IDXM = msb
        IDXL = lsb
        IDL = lsb_1st
        """

        rd_off      = 0
        rst_off     = 0
        rst_wid     = 0
        msb_off     = 0
        msb_wid     = 0
        lsb_fc_wid2 = 0
        lsb_fc_off1 = 0
        rd_wid      = 0
        lsb_fc_wid1 = 0
        lsb_fc_off2 = 0
        lsb_wid     = 0
        lsb_off     = 0
        inv         = 0

        if enable:
            clock = 1./self.FPGA_FREQ_MHZ * 1000. # clock now in ns
            denominator = clock/mult
            period_val = period // denominator

            rd_off      = int(offset_read // denominator) & 0xFFFF
            rst_off     = int(offset_rst // denominator) & 0xFFFF
            rst_wid     = int(width_rst // denominator) & 0xFFFF
            msb_off     = int(offset_msb // denominator) & 0xFFFF
            msb_wid     = int(width_msb // denominator) & 0xFFFF
            lsb_fc_wid2 = int(width_lsb_1st_2 // denominator) & 0xFFFF
            lsb_fc_off1 = int(offset_lsb_1st_1 // denominator) & 0xFFFF
            rd_wid      = int(width_read // denominator) & 0xFFFF
            lsb_fc_wid1 = int(width_lsb_1st_1 // denominator) & 0xFFFF
            lsb_fc_off2 = int(offset_lsb_1st_2 // denominator) & 0xFFFF
            lsb_wid     = int(width_lsb // denominator) & 0xFFFF
            lsb_off     = int(offset_lsb // denominator) & 0xFFFF

            if inv_rst:
              inv += 1 << 0
            if inv_read:
              inv += 1 << 1
            if inv_msb:
              inv += 1 << 2
            if inv_lsb:
              inv += 1 << 3
            if inv_lsb_1st:
              inv += 1 << 4

        def writeRegAndPrint(name,reg,val):
            #print("ExtClock Register {0:15} number {1:3} set to {2:10} = {2:#010x}".format(name,reg,val))
            #print("ExtClock Register {0:15} number {1:3} set to {2:#034b}".format(name,reg,val))
            self.femb.write_reg(reg,val)
        writeRegAndPrint("inv", self.REG_EXTCLK_INV,inv),
        for iChip, regBase in enumerate(self.REG_EXTCLK_BASES):
            iStr = str(iChip)
            asicRegs = [
                ("RST_ADC"+iStr,(rst_wid << 16) | rst_off),
                ("READ_ADC"+iStr,(rd_wid << 16) | rd_off),
                ("IDXM_ADC"+iStr,(msb_wid << 16) | msb_off), # msb
                ("IDXL_ADC"+iStr,(lsb_wid << 16) | lsb_off), # lsb
                ("IDL1_ADC"+iStr,(lsb_fc_wid1 << 16) | lsb_fc_off1), # lsb_fc_1
                ("IDL2_ADC"+iStr,(lsb_fc_wid2 << 16) | lsb_fc_off2), # lsb_fc_1
            ]
            for iReg, tup in enumerate(asicRegs):
                name = tup[0]
                val = tup[1]
                writeRegAndPrint(name,regBase+iReg,val)

    def setExtClockRegs(self, asicNum):
        if asicNum == None :
            return None
        asicNumVal = int(asicNum)
        if (asicNumVal < 0)  or (asicNumVal >= self.NASICS ):
            return None

        #For ADC1
        if asicNumVal == 0 :
            #Coarse Control
            self.femb.write_reg(10, 0x03030303) #Invert/Disable all ADC Clocks         
            self.femb.write_reg(11, 0x00090000) #ADC1 - RST Offset and Width
            self.femb.write_reg(12, 0x0003005E) #ADC1 - READ Offset and Width
            self.femb.write_reg(13, 0x0035002C) #ADC1 - IDXM Offset and Width
            self.femb.write_reg(14, 0x0003005E) #ADC1 - IDXL Offset and Width
            self.femb.write_reg(15, 0x00250008) #ADC1 - IDL1 Offset and Width
            self.femb.write_reg(16, 0x0003005D) #ADC1 - IDL2 Offset and Width

            #Fine Control
            self.femb.write_reg(17, 0x00140011) #ADC1 - READ and IDXM Phase Shift
            self.femb.write_reg(18, 0x0009000F) #ADC1 - IDXL and IDL1 Phase Shift
            self.femb.write_reg(19, 0x00180005) #ADC1 - IDL2 Phase Shift and inversion
            self.femb.write_reg(19, 0x80180005) #ADC1 - OK

        #For ADC2
        if asicNumVal == 1 :
            #Coarse Control
            self.femb.write_reg(10, 0x03030301) #Invert/Disable all ADC Clocks         
            self.femb.write_reg(11, 0x00090000) #ADC2 - RST Offset and Width
            self.femb.write_reg(12, 0x0003005E) #ADC2 - READ Offset and Width
            self.femb.write_reg(13, 0x0035002C) #ADC2 - IDXM Offset and Width
            self.femb.write_reg(14, 0x0003005E) #ADC2 - IDXL Offset and Width
            self.femb.write_reg(15, 0x00250007) #ADC2 - IDL1 Offset and Width
            self.femb.write_reg(16, 0x0003005D) #ADC2 - IDL2 Offset and Width

            #Fine Control
            self.femb.write_reg(17, 0x0012000B) #ADC2 - READ and IDXM Phase Shift
            self.femb.write_reg(18, 0x0006000D) #ADC2 - IDXL and IDL1 Phase Shift
            self.femb.write_reg(19, 0x00180003) #ADC2 - IDL2 Phase Shift and inversion
            self.femb.write_reg(19, 0x80180003) #ADC2 - OK

        #For ADC3
        if asicNumVal == 2 :
            #Coarse Control
            self.femb.write_reg(10, 0x03030303) #Invert/Disable all ADC Clocks         
            self.femb.write_reg(11, 0x00090000) #ADC3 - RST Offset and Width
            self.femb.write_reg(12, 0x0003005E) #ADC3 - READ Offset and Width
            self.femb.write_reg(13, 0x0034002C) #ADC3 - IDXM Offset and Width
            self.femb.write_reg(14, 0x0003005E) #ADC3 - IDXL Offset and Width
            self.femb.write_reg(15, 0x00250008) #ADC3 - IDL1 Offset and Width
            self.femb.write_reg(16, 0x0003005D) #ADC3 - IDL2 Offset and Width

            #Fine Control
            self.femb.write_reg(17, 0x00070017) #ADC3 - READ and IDXM Phase Shift
            self.femb.write_reg(18, 0x00090014) #ADC3 - IDXL and IDL1 Phase Shift
            self.femb.write_reg(19, 0x001A0006) #ADC3 - IDL2 Phase Shift and inversion
            self.femb.write_reg(19, 0x801A0006) #ADC3 - OK

        #For ADC4
        if asicNumVal == 3 :
            #Coarse Control
            self.femb.write_reg(10, 0x03030303) #Invert/Disable all ADC Clocks         
            self.femb.write_reg(11, 0x00090000) #ADC4 - RST Offset and Width
            self.femb.write_reg(12, 0x0003005E) #ADC4 - READ Offset and Width
            self.femb.write_reg(13, 0x0035002C) #ADC4 - IDXM Offset and Width
            self.femb.write_reg(14, 0x0003005E) #ADC4 - IDXL Offset and Width
            self.femb.write_reg(15, 0x00250007) #ADC4 - IDL1 Offset and Width
            self.femb.write_reg(16, 0x0003005D) #ADC4 - IDL2 Offset and Width

            #Fine Control
            self.femb.write_reg(17, 0x000A000A) #ADC4 - READ and IDXM Phase Shift
            self.femb.write_reg(18, 0x0006000A) #ADC4 - IDXL and IDL1 Phase Shift
            self.femb.write_reg(19, 0x001F0004) #ADC4 - IDL2 Phase Shift and inversion
            self.femb.write_reg(19, 0x801F0004) #ADC4 - OK

    def turnOffAsics(self):
        self.femb.write_reg_bits( self.REG_PWR_CTRL , 0, 0xF, 0x0 )
        #pause after turning off ASICs
        time.sleep(2)

    def turnOnAsic(self,asic):
        if asic == None :
            return None
        asicVal = int(asic)
        if (asicVal < 0 ) or (asicVal >= self.NASICS ) :
            print( "femb_config_femb : turnOnAsics - invalid ASIC number, only 0 to {} allowed".format(self.NASICS-1))
            return None

        #check if ASIC is already on in attempt to save time
        regVal = self.femb.read_reg(self.REG_PWR_CTRL)
        if regVal == None :
            return None
        isAsicOn = int(regVal)
        isAsicOn = ((isAsicOn >> asicVal) & 0x1)
        #print("isAsicOn ", hex(regVal), isAsicOn)
        if isAsicOn == 0x1 :
           return

        print("Turning on ASIC ",asicVal)
        self.femb.write_reg_bits( self.REG_PWR_CTRL , asicVal, 0x1, 0x1 )
        time.sleep(5) #pause after turn on

    def turnOnAsics(self):
        print( "turnOnAsics 0-{}".format(int(self.NASICS -1)))
        for iAsic in range(0,self.NASICS,1):
            self.turnOnAsic(iAsic)

    def setFPGADac(self,amp,mode,freq,delay):
        """
        mode: 0 DAC only, 1 ext tp, 2 gnd, 3 1.8V, 4 test pulse, 5 1.8V FE, 6 ASIC TP DAC
        """
        ampRegVal = ((mode & 0xFFFF) << 16) | (amp & 0xFFFF)
        freqRegVal = ((delay & 0xFFFF) << 16) | (freq & 0xFFFF)

        self.femb.write_reg(self.REG_DAC2,freqRegVal)
        time.sleep(0.05)
        self.femb.write_reg(self.REG_DAC1,ampRegVal)
        time.sleep(0.05)
        self.femb.write_reg(self.REG_DAC1,ampRegVal & 0x80000000)
        time.sleep(0.05)
        self.femb.write_reg(self.REG_DAC1,ampRegVal)
        
    def writePLLs(self, step0, step1, step2):
        for iChip in range(0,3,1):
            self.writePLL(iChip,step0,step1,step2)

    def writePLL(self, asic, step0, step1, step2):
        if asic == None :
            return None
        asicVal = int(asic)
        if (asicVal < 0 ) or (asicVal >= self.NASICS ) :
            print( "femb_config_femb : writePLL - invalid ASIC number, only 0 to {} allowed".format(self.NASICS-1))
            return

        regBase = self.REG_PLL_BASES[asicVal]
        self.femb.write_reg(regBase + 0, step0)
        self.femb.write_reg(regBase + 1, step1)
        self.femb.write_reg(regBase + 2, step2)
