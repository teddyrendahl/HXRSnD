#!/usr/bin/python
#Bob Nagler, October 2012, simple code that defines a 2d beamblock

import numpy as n
from numpy import rad2deg,arcsin,sqrt,tan
import sys
from utilities import estr
from utilitiesMotors import tweak2d
import pypsepics
from pypslog import logprint

class BeamBlock2D:
  """ Class to control a simple beamblock on an xy stage """

  def __init__(self,bbx,bby,inpos_x_pv,inpos_y_pv,outpos_x_pv,outpos_y_pv,desc="2D BeamBlock"):
    self.x = bbx
    self.y=bby

    self._inpos_x_pv=inpos_x_pv
    self._inpos_y_pv=inpos_y_pv
    self._outpos_x_pv=outpos_x_pv
    self._outpos_y_pv=outpos_y_pv

    self.__desc = desc

  def inposx(self):
    return pypsepics.get(self._inpos_x_pv)

  def inposy(self):
    return pypsepics.get(self._inpos_y_pv)

  def outposx(self):
    return pypsepics.get(self._outpos_x_pv)

  def outposy(self):
    return pypsepics.get(self._outpos_y_pv)

  def status(self):
    str = "\nbeam block position is "
    if abs(self.x.wm() - self.inposx()) < 0.01 and abs(self.y.wm() - self.inposy()) < 0.01:
      str += estr("IN",color="green",type="normal")
    elif abs(self.x.wm() - self.outposx()) < 0.1 and abs(self.y.wm() - self.outposy()) < 0.1 :
      str += estr("OUT", color="yellow",type="bold")
    else: str+= estr("UNKNOWN",color="red",type="bold")
    
    return str

  def move_in(self):
    print "moving beamblock in...\n"
    self.x.umv(self.inposx())
    self.y.umv(self.inposy())
    print "beamblock is in. "

  def move_out(self):
    print "moving beamblock out...\n"
    self.x.umv(self.outposx())
    self.y.umv(self.outposy())
    print "beamblock is out. "

  def tweak(self):
    tweak2d(self.x,self.y)

  def set_in_pos(self):
    ''' makes the current position of the beamblock the new in position'''
    pypsepics.put(self._inpos_x_pv,self.x.wm())
    pypsepics.put(self._inpos_y_pv,self.y.wm())

  def set_out_pos(self):
    '''makes the current position of the beamblock the new out position'''
    pypsepics.put(self._outpos_x_pv,self.x.wm())
    pypsepics.put(self._outpos_y_pv,self.y.wm())

    


  
  def __repr__(self):
    return self.status()
