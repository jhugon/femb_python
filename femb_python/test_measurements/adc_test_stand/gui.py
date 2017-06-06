"""
ADC Test Stand GUI
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
import datetime
import socket
import os
import os.path
import pwd
import sys
import glob
import json
from time import sleep
from tkinter import *
import subprocess

#import the test module
from ...configuration import CONFIG
from .run import runTests
from ...runpolicy import DirectRunner, SumatraRunner

class GUI_WINDOW(Frame):

    #GUI window defined entirely in init function
    def __init__(self, master=None):
        Frame.__init__(self,master)
        self.pack()

        self.config = CONFIG()

        self.timestamp = None
        self.result_labels = []
        self.display_procs = []
        #Define general commands column
        self.define_test_details_column()
        self.reset()

        self.master.protocol("WM_DELETE_WINDOW", self.exit)

    def define_test_details_column(self):
        columnbase=0

        # Adding operator name label and read entry box
        self.operator_label = Label(self,text="Operator Name:",width=25)
        self.operator_label.grid(sticky=W,row=1,column=columnbase+0)

        self.operator_entry = Entry(self,width=25)
        self.operator_entry.grid(sticky=W,row=1,column=columnbase+1)

        # Adding electronics ID and read entry box
        self.boardid_label = Label(self,text="Test Board ID:",width=25)
        self.boardid_label.grid(sticky=W,row=3,column=columnbase+0)

        self.boardid_entry = Entry(self,width=25)
        self.boardid_entry.grid(sticky=W,row=3,column=columnbase+1)

        # ASIC IDs
        self.asic_entries = []
        self.asic_labels = []
        for i in range(self.config.NASICS):
            label = Label(self,text="ASIC {} ID:".format(i),width=25)
            label.grid(sticky=W,row=6+i,column=columnbase+0)

            asic_entry = Entry(self,width=25)
            asic_entry.grid(sticky=W,row=6+i,column=columnbase+1)

            self.asic_labels.append(label)
            self.asic_entries.append(asic_entry)

        self.prepare_button = Button(self, text="Power-up Board", command=self.prepare_board,width=25)
        self.prepare_button.grid(row=20,column=columnbase,columnspan=2)

        # Adding electronics ID and read entry box
        self.current_label = Label(self,text="CH2 Current [A]:",width=25,state="disabled")
        self.current_label.grid(sticky=W,row=21,column=columnbase+0)

        self.current_entry = Entry(self,width=25,state="disabled")
        self.current_entry.grid(sticky=W,row=21,column=columnbase+1)

        self.start_button = Button(self, text="Start Tests", command=self.start_measurements,width=25)
        self.start_button.grid(row=22,column=columnbase,columnspan=2)
        self.reset_button = Button(self, text="Reset & Power-off", command=self.reset,width=25,bg="#FF8000")
        self.reset_button.grid(row=24,column=columnbase,columnspan=2)

        self.runid_label = Label(self, text="")
        self.runid_label.grid(row=25,column=columnbase,columnspan=2)

        self.status_label = Label(self, text="NOT STARTED",bd=1,relief=SUNKEN,width=50)
        self.status_label.grid(row=100,column=columnbase,columnspan=2)
        self.bkg_color = self.status_label.cget("background")

    def get_options(self,getCurrent=False):
        operator = self.operator_entry.get()
        boardid = self.boardid_entry.get()
        current = None
        if getCurrent:
            current = self.current_entry.get()
        # ASIC IDs
        asic_ids = []
        for i in range(self.config.NASICS):
            try:
                serial = self.asic_entries[i].get()
                serial = int(serial)
                asic_ids.append(serial)
            except ValueError:
                return

        variables = [operator,boardid]+asic_ids
        for var in variables:
            if var == "" :
                return
        if getCurrent:
            if current == "":
                return
            try:
                current = float(current)
            except:
                return

        print("Operator Name: '{}'".format(operator))
        print("Test Board ID: '{}'".format(boardid))
        for i in range(self.config.NASICS):
            print("ASIC {} ID: '{}'".format(i,asic_ids[i]))

        # need serialnumber list, operator, board_id, timestamp, hostname
        timestamp = self.timestamp
        if timestamp is None:
            timestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
        self.timestamp = timestamp
        hostname = socket.gethostname() 
        chipidstr = ""
        for i in asic_ids:
            chipidstr += str(i) + ","
        chipidstr = chipidstr[:-1]
        runid = "{} {} chip: {}".format(hostname,timestamp, chipidstr)
        print("runid: '{}'".format(runid))
        femb_config_name = os.environ["FEMB_CONFIG"]
        linux_username = pwd.getpwuid(os.getuid()).pw_name
        inputOptions = {
            "operator": operator,
            "board_id": boardid,
            "serials": asic_ids,
            "timestamp": timestamp,
            "hostname": hostname,
            "runid": runid,
            "femb_config_name": femb_config_name,
            "linux_username": linux_username,
            "smttag": hostname,
        }
        if getCurrent:
            inputOptions["current"] = current
        pghost = os.environ.get("PGHOST")
        if pghost:
            print ("Using PostgreSQL database at %s" % pghost)
            inputOptions.update(
                smtstore="postgres://{pguser}@{pghost}/{pgdatabase}",
                pguser = os.environ['PGUSER'],
                pghost = os.environ['PGHOST'],
                pgdatabase = os.environ['PGDATABASE'],
            )
        else:
            print ("Using Sqlite3 database in rundir")
        print(inputOptions)
        return inputOptions

    def reset(self):
        print("POWER DOWN")
        self.config.POWERSUPPLYINTER.off()
        self.timestamp = None
        for i in reversed(range(len(self.display_procs))):
            tmp = self.display_procs.pop(i)
            tmp.terminate()
            try:
                tmp.wait(2)
            except subprocess.TimeoutExpired:
                tmp.kill()
            del tmp
        for i in reversed(range(len(self.result_labels))):
            tmp = self.result_labels.pop(i)
            tmp.destroy()
        self.status_label["text"] = "NOT STARTED"
        self.status_label["fg"] = "#000000"
        self.status_label["bg"] = self.bkg_color
        self.runid_label["text"] = ""
        self.prepare_button["state"] = "normal"
        self.start_button["state"] = "disabled"
        self.operator_label["state"] = "normal"
        self.operator_entry["state"] = "normal"
        self.boardid_label["state"] = "normal"
        self.boardid_entry["state"] = "normal"
        self.current_label["state"] = "disabled"
        self.current_entry["state"] = "normal"
        self.current_entry.delete(0,END)
        self.current_entry["state"] = "disabled"
        #self.operator_entry.delete(0,END)
        #self.boardid_entry.delete(0,END)
        for i in range(self.config.NASICS):
            self.asic_labels[i]["state"] = "normal"
            self.asic_entries[i]["state"] = "normal"
            self.asic_entries[i].delete(0,END)
        self.reset_button["bg"] ="#FF9900"
        self.reset_button["activebackground"] ="#FFCF87"

    def prepare_board(self):
        inputOptions = self.get_options()
        if inputOptions is None:
            print("ENTER REQUIRED INFO")
            self.status_label["text"] = "ENTER REQUIRED INFO"
            self.status_label["fg"] = "#FF0000"
            return
        print("BEGIN PREPARE")
        self.status_label["text"] = "POWERING UP BOARD..."
        self.status_label["fg"] = "#000000"
        self.runid_label["text"] = "Run ID: "+ inputOptions["runid"]

        self.update_idletasks()
        self.config.POWERSUPPLYINTER.on()
        sleep(1)
        self.config.resetBoard()
        self.config.initBoard()
        self.config.syncADC()
        self.done_preparing_board()

    def start_measurements(self):
        inputOptions = self.get_options(getCurrent=True)
        if inputOptions is None:
            print("ENTER REQUIRED INFO")
            self.status_label["text"] = "ENTER FLOAT FOR CURRENT"
            self.status_label["fg"] = "#FF0000"
            return
        self.current_label["state"] = "disabled"
        self.current_entry["state"] = "disabled"
        self.start_button["state"] = "disabled"

        print("BEGIN TESTS")
        self.status_label["text"] = "TESTS IN PROGRESS..."
        self.status_label["fg"] = "#000000"
        self.update_idletasks()

        data_base_dir = "/dsk/1/data"
        try:
            data_base_dir = os.environ["FEMB_DATA_DIR"]
        except KeyError:
            pass

        runnerSetup = {
                                "executable": "femb_adc_run",
                                #"argstr": "--quick -j {paramfile}",
                                "argstr": "-j {paramfile}",
                                "basedir": data_base_dir,
                                "rundir": "{basedir}/adc/{hostname}",
                                "datadir": "{rundir}/Data/{timestamp}",
                                "paramfile": "{datadir}/params.json",
                                "smtname": "adc",
                            }
        #runner = DirectRunner(**runnerSetup)
        runner = SumatraRunner(**runnerSetup)
        try:
            params = runner(**inputOptions)
            #params = runner.resolve(**inputOptions) # use to test GUI w/o running test
        except RuntimeError:
            self.status_label["text"] = "Error in test program. Report to shift leader"
            self.status_label["fg"] = "#FFFFFF"
            self.status_label["bg"] = "#FF0000"
            return
        else:
            self.done_measuring(params)

    def done_preparing_board(self):
        ## once prepared....
        print("BOARD POWERED UP & INITIALIZED")
        self.current_label["state"] = "normal"
        self.current_entry["state"] = "normal"
        self.status_label["text"] = "Power up success, enter CH2 Current"
        self.status_label["fg"] = "#000000"
        self.prepare_button["state"] = "disabled"
        self.start_button["state"] = "normal"
        self.operator_label["state"] = "disabled"
        self.operator_entry["state"] = "disabled"
        self.boardid_label["state"] = "disabled"
        self.boardid_entry["state"] = "disabled"
        for i in range(self.config.NASICS):
            self.asic_labels[i]["state"] = "disabled"
            self.asic_entries[i]["state"] = "disabled"

    def done_measuring(self,params):
        print("TESTS COMPLETE")
        self.status_label["text"] = "Tests done"
        self.reset_button["bg"] ="#00CC00"
        self.reset_button["activebackground"] = "#A3CCA3"
        datadir = params["datadir"]
        timestamp = params["timestamp"]
        #datadir = "/home/jhugon/data/adc/hothdaq4/olddata/2017-06-02T14:24:54"
        #timestamp = "2017-06-02T14:24:54"
        outfileglob = "adcTest_{}_*.json".format(timestamp)
        outfileglob = os.path.join(datadir,outfileglob)
        #print(outfileglob)
        outfilenames = glob.glob(outfileglob)
        print(outfilenames)
        if len(outfilenames) != self.config.NASICS:
            self.status_label["text"] = "Error: Test output not found. Report to shift leader"
            self.status_label["fg"] = "#FFFFFF"
            self.status_label["bg"] = "#FF0000"
            return
        titles_made = False
        testNames = None
        columnbase = 0
        rowbase = 50
        for iCol,outfilename in enumerate(sorted(outfilenames)):
            data = None
            with open(outfilename) as outfile:
                data = json.load(outfile)
            results = data["testResults"]
            serial = data["serial"]
            theseTestNames = sorted(list(results.keys()))
            theseTestNames.pop(theseTestNames.index("pass")) # don't want in list
            if titles_made:
                assert(theseTestNames == testNames)
            else:
                testNames = theseTestNames
                label = Label(self, text="Test",anchor=W)
                label.grid(row=rowbase,column=columnbase)
                self.result_labels.append(label)
            label = Label(self, text=serial)
            label.grid(row=rowbase,column=columnbase+1+iCol)
            self.result_labels.append(label)
            # overall pass fail
            if results["pass"]:
                label = Label(self, text="PASS",bg="#00CC00")
                label.grid(row=rowbase+2,column=columnbase+1+iCol)
                self.result_labels.append(label)
            else:
                label = Label(self, text="FAIL",bg="#FF0000")
                label.grid(row=rowbase+2,column=columnbase+1+iCol)
                self.result_labels.append(label)
            label = Label(self, text="") # just to put a blank space
            label.grid(row=rowbase+3,column=columnbase+1+iCol)
            self.result_labels.append(label)
            # individual tests:
            for iTest, test in enumerate(testNames):
                if not titles_made:
                    label = Label(self, text=test,anchor=E,justify=LEFT)
                    label.grid(row=rowbase+iTest+5,column=columnbase)
                    self.result_labels.append(label)
                color = "#FF0000"
                text = "FAIL"
                if results[test]:
                    color = "#00CC00"
                    text = "OK"
                label = Label(self, text=text,width=4,bg=color)
                label.grid(row=rowbase+iTest+5,column=columnbase+1+iCol)
                self.result_labels.append(label)
            titles_made = True
        imgfileglob = "adcTest_{}_*.png".format(timestamp)
        imgfileglob = os.path.join(datadir,imgfileglob)
        print(imgfileglob)
        imgfilenames = glob.glob(imgfileglob)
        print(imgfilenames)
        for imgfilename in imgfilenames:
            self.display_procs.append(subprocess.Popen(["display","-resize","800x800",imgfilename]))

    def exit(self,*args, **kargs):
        for i in reversed(range(len(self.display_procs))):
            tmp = self.display_procs.pop(i)
            tmp.terminate()
            try:
                tmp.wait(4)
            except subprocess.TimeoutExpired:
                tmp.kill()
            del tmp
        self.destroy()
        self.master.destroy()

def main():
    root = Tk()
    root.title("ADC Test GUI")
    window = GUI_WINDOW(root)
    root.mainloop() 
