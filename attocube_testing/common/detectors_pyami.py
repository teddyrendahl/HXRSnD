#!/usr/bin/python
# This module provides support for PV based monitors
# 
# Author:         Marco Cammarata (SLAC)
# Created:        Aug 5, 2010
# Modifications:
#   Aug 5, 2010 MC
#       first version

import pyami
import numpy
from numpy import nan,array,sqrt,isfinite
from pypslog import logprint
from time import sleep


class PYAMIdetector:
  """A simple class to handle PV based detectors"""
  def __init__(self,ami_name,mne_name):
    self.aminame = ami_name
    self.name   = mne_name
    self.pyamiE = None

  def connect(self):
    if (self.pyamiE is not None): return
    try:
      self.pyamiE  = pyami.Entry(self.aminame)
    except RuntimeError:
      s = "detector %s cannot be found" % self.name
      logprint(s,print_screen=True)
      self.pyamiE = None


  def get(self):
    self.connect()
    if (self.pyamiE is None):
      x={}
      x["entries"]=0
      x["mean"] = numpy.nan
      x["rms"] = numpy.nan
      x["err"] = numpy.nan
    else:
      x = self.pyamiE.get()
      x["err"] = x["rms"]/sqrt(x["entries"])
    return x

  def getmean(self,int_time=None):
    self.connect()
    if (self.pyamiE is None):
      return numpy.nan
    else:
      if (int_time is not None):
        self.clear()
        sleep(int_time)
      x = self.get()
      return x["mean"]

  def clear(self):
    self.pyamiE.clear()
#    ret=dict()
#    if (config.DEBUG>1):
#      print "Detector.monitor_get, len(self.__monitorlist)=%d" % len(self.__monitorlist)
#    if (len(self.__monitorlist)==0):
#      ret["mean"]=nan
#      ret["std"]=nan
#      ret["num"]=nan
#      ret["err"]=nan
#      print "No pulses...."
#      return ret
#    mynums=[]
#    for el in self.__monitorlist:
#      idx = el.rfind(" ")+1; # index of last whitespace+1
#      num = float( el[ idx:-1 ] )
#      mynums.append(num)
#    mynums=array(mynums)
#    # remove "bad readings"
#    mynums = mynums[isfinite(mynums)]
#    ret["mean"]=mynums.mean()
#    ret["std"] =mynums.std()
#    ret["num"] =len(mynums)
#    ret["err"] =ret["std"]/sqrt(ret["num"])
#    return ret
      
class IPIMBDetector:
  """A simple class to handle Pv based detectors"""
  def __init__(self,aminame,namebase="detector",kind="NotKnown",timeout=15):
    self.__kind = kind
    if (namebase == ""):
      namebase = pvname
    self.ch0  = PYAMIdetector( aminame + ":CH0" ,namebase+".ch0" )
    self.ch1  = PYAMIdetector( aminame + ":CH1" ,namebase+".ch1" )
    self.ch2  = PYAMIdetector( aminame + ":CH2" ,namebase+".ch2" )
    self.ch3  = PYAMIdetector( aminame + ":CH3" ,namebase+".ch3" )
    self.sum  = PYAMIdetector( aminame + ":SUM" ,namebase+".sum")
    self.xpos = PYAMIdetector( aminame + ":XPOS",namebase+".xpos")
    self.ypos = PYAMIdetector( aminame + ":YPOS",namebase+".ypos")

  def __repr__(self):
    return self.status()

  def status(self):
    str=""
    if (self.__kind=="ipm"):
      str  = " %10s %6s %6s %10s %10s %10s %10s\n" % ("sum", "xpos","ypos","ch0(up)","ch1(north)","ch2(down)","ch3(south)")
      str += "  %+10.3e %+6.3f %+6.3f " % ( self.sum.getmean(0.3),self.xpos.getmean(0.3),self.ypos.getmean(0.3) )
      str += "%10.3e %10.3e %10.3e %10.3e\n" % ( self.ch0.getmean(0.3),self.ch1.getmean(0.3),self.ch2.getmean(0.3),self.ch3.getmean(0.3) )
    if (self.__kind=="pim"):
      str  = " %10s %10s %10s %10s\n" % ("ch0(up)","ch1(north)","ch2(down)","ch3(south)")
      str += "%10.3e %10.3e %10.3e %10.3e\n" % ( self.ch0.getmean(0.3),self.ch1.getmean(0.3),self.ch2.getmean(0.3),self.ch3.getmean(0.3) )
    return str
