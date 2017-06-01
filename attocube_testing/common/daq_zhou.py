from utilities import notice

try:
  import pydaq
except:
  print "pydaq module is not found"
  print "Please run \"source pydaq_setup.bash\", or update your env path"
  sys.exit(1)

import pypsepics
import detectors
import sys
import signal
import motor
import virtualmotor
import motor_PV
import time
from time import sleep
from datetime import datetime
from numpy import abs,array,nan
import config
import KeyPress
import os
from glob import glob
import pyami
import pylab
import PeakAnalysis
import numpy as np
import threading
from socket import gethostname


class Daq:
  def __init__(self,host="mec-console",platform=0):
    self._host=host
    self._platform=platform
    self.__daq = None
    self.__scanstr = None
    self.__monitor=None
    self.__dets = None
    self.__filter_det = None
    self.__filter_min = None
    self.__filter_max = None
    self.__npulses = None
    self.__running=False
    self.issingleshot=0
    self.plot=None
    self.doplot=True
    self.record=None
    self.scan_in_ext_window=False
    self.settling_time = 0.    
    
    
  def status(self):
    s  = "DAQ status\n"
    if (self.record is None):
      s += "  Recording RUN: selected by GUI\n"
    elif (self.record):
      s += "  Recording RUN: YES\n"
    elif (not self.record):
      s += "  Recording RUN: NO\n"
    return s

  def __repr__(self):
    return self.status()

  def connect(self):
    self.disconnect()   
    self.__daq = pydaq.Control(self._host,self._platform)    
    if self.__daq:
      self.__daq.connect() 
    return self.__daq

  def disconnect(self):
    if self.__daq != None:
      self.__daq.disconnect()
      del self.__daq
    self.__daq = None

  def daqconnect(self):
    self.__daq.connect()
    return self.__daq

  def daqdisconnect(self):
    self.__daq.disconnect()

  def clear_daq_l3t(self):
    pyami.clear_l3t()

  def configure(self,events,key=None,controls=[],monitors=[],labels=[], count_selected=0):
    """ note: controls,monitors and labels have to be list of tuple
        and NOT list of list """
    self.connect()
    #insert call for trigger here
    #if (self.__filter_det is not None):
    #  filter_aminame = self.__filter_det.aminame
    #  filter_str = "%f<%s<%f" % (self.__filter_min,filter_aminame,self.__filter_max)
      
    if key==None:
      key = self.__daq.dbkey()
      

    if (self.record is None):
      print "Record is what you set in GUI"
      if (count_selected==0):
        self.__daq.configure(events=events, key=key,
                             controls=controls,monitors=monitors,labels=labels)
        #print 'configure w/ controls: ',controls
      else:
        self.__daq.configure(l3t_events=events, key=key,
                             controls=controls,monitors=monitors,labels=labels)
        #print 'configure w/ controls: ',controls
    else:
      print "Record is: " , bool(self.record), " (l3t)"
      if (count_selected==0):
        self.__daq.configure(record=bool(self.record),events=events, key=key,
                           controls=controls,monitors=monitors,labels=labels)
      else:
        self.__daq.configure(record=bool(self.record),l3t_events=events, key=key,
                             controls=controls,monitors=monitors,labels=labels)



  def begin(self,events=None,duration=None,controls=[],monitors=[],labels=[], count_selected=0):
    if (self.__daq is None):
      self.configure(events,None,controls,monitors,labels=labels, count_selected=count_selected)
    self.__running=True
    if (events is not None):
      if (count_selected==0):
        print "how many events %s" % events
        self.__daq.begin(events=events,controls=controls,monitors=monitors,labels=labels)
      else:
        self.__daq.begin(l3t_events=events,controls=controls,monitors=monitors,labels=labels)
    elif (duration is not None):
      sec = int(duration)
      nsec = int ( (duration-sec )*1e9 )
      duration = [sec,nsec]
      self.__daq.begin(duration=duration,controls=controls,monitors=monitors,labels=labels)
    else:
      self.__daq.begin(controls,monitors); # use default number of events set with configure
      

  def wait(self):
    if (self.__running):
      self.__daq.end()
      self.__running=False


  def stop(self):
    if (self.__running):
      self.__daq.stop()
      self.__running=False


  def runnumber(self):
    if (self.__daq is not None):
      return self.__daq.runnumber()
    else:
      return 0

  def eventnum(self):
    if (self.__daq is not None) and self.__running:
      return self.__daq.eventnum()
    else:
      return 0

  def dbalias(self):
    if (self.__daq is not None):
      return self.__daq.dbalias()
    else:
      return ""

  def dbkey(self):
    if (self.__daq is not None) and self.__running:
      return self.__daq.dbkey()
    else:
      return 0

  def dbpath(self):
    if (self.__daq is not None):
      return self.__daq.dbpath()
    else:
      return ""

  def calibcycle(self,events=None,controls=[],monitors=[],count_selected=0):
    t0=time.time()
    self.__npulses=events
    if (self.__daq is None): self.configure(events,None, \
            controls=controls,monitors=monitors,count_selected=count_selected)
    self.begin(events=events,controls=controls,monitors=monitors,count_selected=count_selected)
    self.wait()
    tneeded = time.time()-t0
    if (config.TIMEIT>0):
      print "Daq.calibcycle: time needed for %d shots: %f" % (events,tneeded)

  def restartDAQ(self,hostname=None):
    answer=raw_input("Sure ? [y/n]\n")
    if (answer[0].lower()=="y"):
      if hostname==None:
        hostname = gethostname()
      os.system('/reg/g/pcds/dist/pds/mec/scripts/restart_mec_daq.csh')

  def stopDAQ(self):
    answer=raw_input("Sure ? [y/n]\n")
    if (answer[0].lower()=="y"):
      os.system('/reg/g/pcds/dist/pds/mec/scripts/shutdown_mec_daq.csh')

