#!/usr/bin/python
# This module provides support 
# for the XCS Large Area Detector Mover (LADM or LAM)
# for the XCS beamline (@LCLS)
# 
# Author:         Daniel Flath (SLAC)
# Created:        Aug 19, 2011
# Modifications:
#   Aug 19, 2011 DF
#       first version

import numpy as n
from numpy import rad2deg,arcsin,sqrt,tan
import sys
from utilities import estr
import pypsepics
from pypslog import logprint

class BeamBlock:
  """ Class to control a simple beamblock on a linear stage """

  def __init__(self,bbmotor,inpos=0,outpos=-103,desc="BeamBlock"):
    self.x = bbmotor
    self.__desc = desc
    self.__in = inpos
    self.__out = outpos

  def status(self):
    str = "\nlaser beam block position is "
    if abs(self.x.wm() - self.__in) < 1:
      str += estr("IN",color="green",type="normal")
    elif abs(self.x.wm() - self.__out) < 2:
      str += estr("OUT", color="red",type="bold")
    else: str+= estr("UNKNOWN",color="red",type="bold")
    
    return str

  def block(self):
    print "moving beamblock in...\n"
    self.x.mv(self.__in)
    #print "beamblock is in. "

  def open(self):
    print "moving beamblock out ...\n"
    self.x.mv(self.__out)
   # print "beamblock is out."

  
  def __repr__(self):
    return self.status()
