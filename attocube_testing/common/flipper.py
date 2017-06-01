import pypsepics
import utilities
import time
from numpy import *
from time import time, sleep
class Flipper(object):
  def __init__(self,pv,name):
    self._name   = name
    self._pv = pv
    

  def __call__(self):
    print self.status()

  def __repr__(self):
    return self.status()

  def isin(self):
      state=pypsepics.get(self._pv)
      if state== 1: return False
      elif state==0: return True

  def status(self):
    s  = "Flipper %s\n" % self._name
    s += "  current position : "
    if self.isin(): s+="in"
    elif not self.isin(): s+="out"
    else: s+="unknown position. This is akward."
    return s

  def flip_in(self):
    pypsepics.put(self._pv,1)

  def flip_out(self):
    pypsepics.put(self._pv,0)

  def flip(self):
    if self.isin(): self.flip_out()
    elif not self.isin(): self.flip_in()
