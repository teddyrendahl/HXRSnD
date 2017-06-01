#!/usr/bin/python
# This module provides support 
# PIM (profile intensity monitor) devices
# for the XPP beamline (@LCLS)
# 
# Author:         Marco Cammarata (SLAC)
# Created:        June 14, 2010
# Modifications:
#   June 14, 2010 MC
#       first version


import numpy as n
import sys
from utilities import estr
import pypsepics

class IBootBar(object):
  """ Class to control the ibbotbar """
  def __init__(self,PVbase="XPP:R39:PWR:03"):
		self.y = screen_motor
		self.zoom  = zoom_lens_motor
#		if not lens_focus_motor==None:
                self.focus = lens_focus_motor
		self.__led = led
		self.__desc = desc
		self.__screen_in_pos = 0
		self.__diode_in_pos = 26
		self.__all_out_pos = -52
		self.__det = det

  def lightoff(self):
    pypsepics.put(self.__led,0);

  def lighton(self,level=100):
    pypsepics.put(self.__led,level);

  def __getlight(self):
    import pyca
    try: 
      l=pypsepics.get(self.__led)
      return l
    except pyca.pyexc:
      return "Not connected"
      
  def screen_in(self):
	  self.y.move(self.__screen_in_pos)
  def diode_in(self):
    if (self.__getlight() != "Not connected" and self.__getlight() > 1):
		  print "Note: the LED light is not off, use .lightoff() to switch it off"
    self.y.move(self.__diode_in_pos)
  def all_out(self):
    self.y.move(self.__all_out_pos)
  def __repr__(self):
    return self.status()
  def status(self):
		str  = estr("%s " % self.__desc,color="black",type="bold")
		pos = self.y.wm()
		if ( abs(pos-self.__screen_in_pos)<5e-3 ):
			str += "screen is %s\n" % estr("IN",type="normal")
		elif ( abs(pos-self.__diode_in_pos)<5e-3 ):
			str += "diode is %s\n" % estr("IN",type="normal")
		elif ( abs(pos-self.__all_out_pos)<5e-3 ):
			str += "all elements are %s\n" % estr("OUT",color="green",type="normal")
		else:
			str += "%s\n" % estr("UNKOWN position",type="normal")
		str += " zoom %.1f%%\n" % self.zoom.wm()
                if (self.focus is not None):
                  str += " focus %.1f%%\n" % self.focus.wm()
		if (self.__led is not None):
			str += " light level %s%%\n" % self.__getlight()
		if (self.__det is not None):
			str += " %s" % self.__det.status()
		return str
