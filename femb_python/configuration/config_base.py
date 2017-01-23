""" 
Base class for configuration files. These should be considered the 'public'
methods of the config classes, non-configuration code should only use this set
of functions.  
"""

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from builtins import int
from builtins import range
from builtins import hex
from builtins import str
from future import standard_library
standard_library.install_aliases()
from builtins import object

class FEMB_CONFIG_BASE(object):
    """
    Base class for configuration files. These should be considered the 'public'
    methods of the config classes, non-configuration code should only use this set
    of functions.  
    """

    def __init__(self):
        """
        Initialize this class (no board communication here. Should setup self.femb as a femb_udp instance.
        """
        self.femb = None

    def resetBoard(self):
        """
        Send reset to board/asics
        """
        pass

    def initBoard(self):
        """
        Initialize board/asics with default configuration
        """
        pass

    def configAdcAsic(self,Adcasic_regs):
        """
        Configure ADCs with given list of registers
        """
        pass

    def configFeAsic_regs(self,feasic_regs):
        """
        Configure FEs with given list of registers
        """
        pass

    def configFeAsic(self,gain,shape,base):
        """
        Configure FEs with given gain/shape/base values
        """
        pass

    def selectChannel(self,asic,chan, hsmode= 1 ):
        """
        Select asic/chan for readout and set hsmode
        """
        pass

    def setInternalPulser(self,pulserEnable,pulseHeight):
        pass

    def syncADC(self):
        """
        Syncronize the ADCs
        """
        pass
