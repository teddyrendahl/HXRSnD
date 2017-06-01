import pypsepics
import utilities
import time
from numpy import *
from time import time, sleep
class ThorlabsFlipper(object):
  def __init__(self,pv,name):
    self._name   = name
    self._pv = pv
    

  def __call__(self):
    print self.status()

  def __repr__(self):
    return self.status()

  def isin(self):
      state=pypsepics.get(self._pv+":STATE")
      if state== 1: return True
      elif state==0: return False

  def status(self):
    s  = "Flipper %s\n" % self._name
    s += "  current position : "
    if self.isin(): s+="in"
    elif not self.isin(): s+="out"
    else: s+="unknown position. This is akward."
    return s

  def flip(self):
    pypsepics.put(self._pv+":TRIG_OUT",1)
    sleep(0.1)
    pypsepics.put(self._pv+":TRIG_OUT",0)

