"""
Module containes an example GUI. The main window configures the FEMB 
while trace_fft_window provides a second window with live trace and FFT.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from builtins import int
from builtins import str
from builtins import hex
from future import standard_library
standard_library.install_aliases()
from time import sleep
from tkinter import *

import os                                 # for statv
import time
import getpass                            # for getuser

#import the test module
#from femb_python.test_measurements.feAsicTest.doFembTest_simpleMeasurement import FEMB_TEST_SIMPLE
#from femb_python.test_measurements.feAsicTest.doFembTest_gainMeasurement import FEMB_TEST_GAIN

from femb_python import runpolicy

class GUI_WINDOW(Frame):

    # defaults
    use_sumatra = True
    datadisks = ["/dsk/1", "/dsk/2"]
    femb_config = "quadFeAsic"               # aka FEMB_CONFIG env var

    #GUI window defined entirely in init function
    def __init__(self, master=None):

        femb_config = os.environ['FEMB_CONFIG']

        Frame.__init__(self,master)
        self.pack()

        #Define general commands column
        self.define_test_details_column()

        #Define general commands column
        self.define_general_commands_column()

        #define required variables
        self.params = dict(
            operator_name = "",
            test_stand = "",
            boardid = "",
            asic0id = "",
            asic1id = "",
            asic2id = "",
            asic3id = "",
            test_category = "feasic",
            test_version = "1",
            femb_config = femb_config
        )

        # Check out the data disk situation and find the most available disk
        freedisks = list()
        for dd in self.datadisks:
            stat = os.statvfs(dd)
            MB = stat.f_bavail * stat.f_frsize >> 20
            freedisks.append((MB, dd))
        freedisks.sort()
        self.params["lo_disk"] = freedisks[0][1]
        self.params["hi_disk"] = freedisks[-1][1]

        now = time.time()
        self.params["session_start_time"] = time.strftime("%Y%m%dT%H%M%S", time.localtime(now))
        self.params["session_start_unix"] = now

        # some hothdaq disk policy, only "oper" gets to write to /dsk/N/data/
        username = getpass.getuser()
        if username == "oper":
            datadisk = "{lo_disk}/data"
        else:
            datadisk = "{lo_disk}/tmp"

        # these are needed for runpolicy Runner
        self.params.update(

            user = username,
            datadisk = datadisk,

            # The rundir is where each individual job starts and should be
            # shared by all jobs.  For Sumatra controlled running this
            # directory houses the .smt/ subdirectory
            rundir = "/home/{user}/run",
            
            # The data dir is where the output of each job should go.  This
            # should be made unique every job.
            datadir = "{datadisk}/{user}/{test_category}/{femb_config}/{session_start_time}/{datasubdir}",

            # This is the file where all these parameters get written
            # after variables are resovled.  This file is made
            # available to the measurement script.  It's a JSON file.
            paramfile = "{datadir}/params.json",

            # This is some "project" name needed by Sumatra
            smtname = "{test_category}",
            );



        # make a runner to enforce consistent run policy for each time an
        # actual measurement scripts is executed.  Prime with parameters as
        # they are known up to know.  They will be overridden and augmented
        # when the runner is called.
        if self.use_sumatra:
            self.runner = runpolicy.SumatraRunner(**self.params)
        self.runner = runpolicy.DirectRunner(**self.params)
        return

    def define_test_details_column(self):
        columnbase=0

        label = Label(self, text="Tests Details")
        label.grid(row=0,column=columnbase, columnspan=50)

        # Adding operator name label and read entry box
        label = Label(self,text="Operator Name:",width=25)
        label.grid(sticky=W,row=1,column=columnbase+0)

        self.operator_entry = Entry(self,width=25)
        self.operator_entry.grid(sticky=W,row=1,column=columnbase+1)

        # Adding test stand ID and read entry box
        label = Label(self,text="Test Stand #:",width=25)
        label.grid(sticky=W,row=2,column=columnbase+0)

        self.test_stand_entry = Entry(self,width=25)
        self.test_stand_entry.grid(sticky=W,row=2,column=columnbase+1)

        # Adding electronics ID and read entry box
        label = Label(self,text="Test Board ID:",width=25)
        label.grid(sticky=W,row=3,column=columnbase+0)

        self.boardid_entry = Entry(self,width=25)
        self.boardid_entry.grid(sticky=W,row=3,column=columnbase+1)

        # ASIC 0 ID
        label = Label(self,text="ASIC 0 ID:",width=25)
        label.grid(sticky=W,row=6,column=columnbase+0)

        self.asic0_entry = Entry(self,width=25)
        self.asic0_entry.grid(sticky=W,row=6,column=columnbase+1)

        # ASIC 1 ID
        label = Label(self,text="ASIC 1 ID:",width=25)
        label.grid(sticky=W,row=7,column=columnbase+0)

        self.asic1_entry = Entry(self,width=25)
        self.asic1_entry.grid(sticky=W,row=7,column=columnbase+1)

        # ASIC 2 ID
        label = Label(self,text="ASIC 2 ID:",width=25)
        label.grid(sticky=W,row=8,column=columnbase+0)

        self.asic2_entry = Entry(self,width=25)
        self.asic2_entry.grid(sticky=W,row=8,column=columnbase+1)

        # ASIC 3 ID
        label = Label(self,text="ASIC 3 ID:",width=25)
        label.grid(sticky=W,row=9,column=columnbase+0)

        self.asic3_entry = Entry(self,width=25)
        self.asic3_entry.grid(sticky=W,row=9,column=columnbase+1)


    def define_general_commands_column(self):
        columnbase=50

        label = Label(self, text="FE ASIC TESTS")
        label.grid(row=0,column=columnbase, columnspan=50)

        #Adding the check test stand button
        start_button = Button(self, text="Start Tests", command=self.start_measurements,width=25)
        start_button.grid(row=1,column=columnbase,columnspan=25)

        self.start_button_result = Label(self, text="NOT STARTED",width=25)
        self.start_button_result.grid(sticky=W,row=1,column=columnbase+25,columnspan=25)

        #Adding the record data button
        #record_data_button = Button(self, text="Record Data", command=self.record_data,width=25)
        #record_data_button.grid(row=2,column=columnbase,columnspan=25)

        self.check_setup_result = Label(self, text="CHECK SETUP - NOT STARTED",width=50)
        self.check_setup_result.grid(sticky=W,row=2,column=columnbase,columnspan=50)

        self.gain_enc_sequence_result = Label(self, text="GAIN+ENC ALL SETTINGS - NOT STARTED",width=50)
        self.gain_enc_sequence_result.grid(sticky=W,row=3,column=columnbase,columnspan=50)

        self.gain_enc_sequence_fpgadac_result = Label(self, text="GAIN+ENC FPGA DAC ALL SETTINGS - NOT STARTED",width=50)
        self.gain_enc_sequence_fpgadac_result.grid(sticky=W,row=4,column=columnbase,columnspan=50)

        """
        #Adding the record data button
        analyze_data_button = Button(self, text="Analyze Data", command=self.analyze_data,width=25)
        analyze_data_button.grid(row=3,column=columnbase,columnspan=25)

        self.analyze_data_result = Label(self, text="",width=25)
        self.analyze_data_result.grid(sticky=W,row=3,column=columnbase+25,columnspan=25)

        #Adding the archive results button
        archive_results_button = Button(self, text="Archive Results", command=self.archive_results,width=25)
        archive_results_button.grid(row=4,column=columnbase,columnspan=25)

        self.archive_results_result = Label(self, text="",width=25)
        self.archive_results_result.grid(sticky=W,row=4,column=columnbase+25,columnspan=25)
        """

    def start_measurements(self):
        self.params['operator_name'] = self.operator_entry.get()
        self.params['test_stand'] = self.test_stand_entry.get()
        self.params['boardid'] = self.boardid_entry.get()
        self.params['asic0id'] = self.asic0_entry.get()
        self.params['asic1id'] = self.asic1_entry.get()
        self.params['asic2id'] = self.asic2_entry.get()
        self.params['asic3id'] = self.asic3_entry.get()
        print("""\
Operator Name: {operator_name}
Test Stand # : {test_stand}
Test Board ID: {boardid}
ASIC 0 ID: {asic0id}
ASIC 1 ID: {asic1id}
ASIC 2 ID: {asic2id}
ASIC 3 ID: {asic3id}
        """.format(**self.params))

        if not self.params['operator_name']:
            print("ENTER REQUIRED INFO")
            self.start_button_result["text"] = "ENTER REQUIRED INFO"
            self.update_idletasks()
            return

        print("BEGIN TESTS")
        self.start_button_result["text"] = "IN PROGRESS"
        self.update_idletasks()

        for method in ["check_setup", "gain_enc_sequence", "gain_enc_sequence_fpgadac", ]:
        #for method in ["gain_enc_sequence_fpgadac", ]:
            LOUD = method.replace("_"," ").upper()
            methname = "do_" + method
            meth = getattr(self, methname)
            if(LOUD == "CHECK SETUP"):
                self.check_setup_result["text"] = LOUD + " - IN PROGRESS"
                
            if(LOUD == "GAIN ENC SEQUENCE"):
                self.gain_enc_sequence_result["text"] = LOUD + " - IN PROGRESS"

            if(LOUD == "GAIN ENC SEQUENCE FPGA DAC"):
                self.gain_enc_sequence_result["text"] = LOUD + " - IN PROGRESS"
                    
            self.update_idletasks()
            try:
                meth()
            except RuntimeError as err:
                print("failed: %s\n%s" % (LOUD, err)) 
                self.start_button_result["text"] = LOUD + " - FAILED"
                getattr(self, method + "_result")["text"] = LOUD + " - FAILED"
                # anything else?
                return
            
            getattr(self, method + "_result")["text"] = LOUD + " - DONE"
            continue

        self.start_button_result["text"] = "DONE"
        self.update_idletasks()

        self.operator_entry.delete(0,1000)
        self.test_stand_entry.delete(0,1000)
        self.boardid_entry.delete(0,1000)
        self.asic0_entry.delete(0,1000)
        self.asic1_entry.delete(0,1000)
        self.asic2_entry.delete(0,1000)
        self.asic3_entry.delete(0,1000)

        print("FINISHED TEST - GUI RESET")

        #self.femb_test.check_setup()
        #if self.femb_test.status_check_setup == 0:
        #    self.check_setup_result["text"] = "TERRIBLE FAILURE"
        #else:
        #    self.check_setup_result["text"] = "SUCCESS"

    
    def do_check_setup(self):
        '''
        Run simple sanity check sequence.
        '''
        print("CHECK SETUP")
        self.check_setup_result["text"] = "CHECK SETUP - IN PROGRESS"
        self.update_idletasks()
        self.test_result = 0
        self.runner(**self.params, datasubdir="check_setup",
                    executable="femb_feasic_simple",
                    argstr="{paramfile}")

    def do_gain_enc_sequence(self):
        '''
        Run a gain and ENC test sequence against all gain, shaping and baselines.
        '''
        testName = str("GAIN ENC SEQUENCE")
        print(str(testName))
        self.gain_enc_sequence_result["text"] = str(testName) + " - IN PROGRESS"
        self.update_idletasks()
        self.test_result = 0
        
        #put loop here, but equivalently can go in script itself
        for g in range(0,4,1):
            for s in range(0,4,1):
                for b in range(0,2,1):

                    # this raises RuntimeError if measurement script fails
                    self.runner(**self.params, datasubdir="gain_enc_sequence-g{gain_ind}s{shape_ind}b{base_ind}",
                                gain_ind = g, shape_ind = s, base_ind = b, femb_num = 0,
                                executable="femb_feasic_gain",
                                argstr="{paramfile}",
                    )

                    continue
                continue
            continue
        return

    def do_gain_enc_sequence_fpgadac(self):
        '''
        Run a gain and ENC test sequence against all gain, shaping and baselines.
        '''
        testName = str("GAIN ENC SEQUENCE FPGA DAC")
        print(str(testName))
        self.gain_enc_sequence_fpgadac_result["text"] = str(testName) + " - IN PROGRESS"
        self.update_idletasks()
        self.test_result = 0
        
        #put loop here, but equivalently can go in script itself
        for g in range(0,4,1):
            for s in range(1,2,1):
                for b in range(0,1,1):

                    # this raises RuntimeError if measurement script fails
                    self.runner(**self.params, datasubdir="gain_enc_sequence_fpgadac-g{gain_ind}s{shape_ind}b{base_ind}",
                                gain_ind = g, shape_ind = s, base_ind = b, femb_num = 0,
                                executable="femb_feasic_gain_fpgadac",
                                argstr="{paramfile}",
                    )

                    continue
                continue
            continue
        return

    # Can add additional testing sequences like as above with a method name
    # like "do_<semantic_label>".

def main():
    root = Tk()
    root.title("Quad FE ASIC Test GUI")
    window = GUI_WINDOW(root)
    root.mainloop() 

if __name__ == '__main__':
    main()
