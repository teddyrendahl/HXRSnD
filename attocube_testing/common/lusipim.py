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
import os
from utilities import estr
import pypsepics

class PIM:
  """ Class to control the XPP PIM """
  def __init__(self,screen_motor,zoom_lens_motor,lens_focus_motor=None,led=None,det=None,desc="PIM",checkMECXRTBelens=None):
		self.y = screen_motor
		self.zoom  = zoom_lens_motor
#		if not lens_focus_motor==None:
                self.focus = lens_focus_motor
		self.__led = led
		self.__desc = desc
		self._screen_in_pos = 0
		self._diode_in_pos = 26
		self._all_out_pos = -51.99999995
		self.__det = det
                self._viewerlauncher=None
                self._checkMECXRTBelens = checkMECXRTBelens

  def viewer(self):
    ''' launches the gui viewer of the YAG screen '''
    if self._viewerlauncher==None : print('No gui file defined for this yag screen')
    else : os.system(self._viewerlauncher)

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
    
  def set_screen_in(self,pos):
    self._screen_in_pos = pos
    
  def set_diode_in(self,pos):
    self._diode_in_pos = pos
    
  def set_all_out(self,pos):
    self._all_out_pos = pos
       
  def screen_in(self):
	  self.y.move(self._screen_in_pos)
          
  def sin(self):
    if self._checkMECXRTBelens is not None:
      XRTBlenPosition = pypsepics.get("MEC:HXM:MMS:02.RBV")
      if XRTBlenPosition < -10.0:
        print "XRT Belens could be in, are you sure for yag3.sin()? Y/[N]"
        token = raw_input()
        if token == 'Y':
          self.screen_in()
        else:
          print "yag3.sin() aborted."
          return
      else:
        self.screen_in()
    else:
      self.screen_in()
          
  def diode_in(self):
    if (self.__getlight() != "Not connected" and self.__getlight() > 1):
		  print "Note: the LED light is not off, use .lightoff() to switch it off"
    self.y.move(self._diode_in_pos)
    
  def all_out(self):
    self.y.move(self._all_out_pos)

  def out(self):
    self.all_out()
    
  def __repr__(self):
    return self.status()
  
  def status(self):
		tolerance=2*self.y.get_par("retry_deadband")
		str  = estr("%s " % self.__desc,color="black",type="bold")
		pos = self.y.wm()
#		if ( abs(pos-self._screen_in_pos)<5e-3 ):
		if ( abs(pos-self._screen_in_pos)<tolerance ):
			str += "screen is %s   " % estr("IN",type="normal")
		elif ( abs(pos-self._diode_in_pos)<tolerance ):
			str += "diode is %s   " % estr("IN",type="normal")
		elif ( pos<self._all_out_pos+tolerance ):
			str += "is %s   " % estr("OUT",color="green",type="normal")
		else:
			str += "%s\n" % estr("UNKOWN position",type="normal")
		str += " zoom %.1f%%\n" % self.zoom.wm()
                if (self.focus is not None):
                  str += " focus %.1f%%\n" % self.focus.wm()
		if (self.__led is not None):
			str += " light level %s%%\n" % self.__getlight()
	#	if (self.__det is not None):
	#		str += " %s" % self.__det.status()
		return str
