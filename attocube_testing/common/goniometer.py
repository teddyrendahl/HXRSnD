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

class Goniometer:
  """ Class to control the XCS LADM """

  def __init__(self,x,y,th,th2,chi,phi,sx,sy,sz,dy,gam,objName="diff"):
     self.x = x
     self.y = y
     self.th = th
     self.th2 = th2
     self.chi = chi
     self.phi = phi
     self.sx = sx
     self.sy = sy
     self.sz = sz
     self.dy = dy
     self.gam = gam
     self.objName = objName
     
     self.motors = {
        "x": x,
        "y": y,
        "th": th,
        "th2": th2,
        "chi": chi,
        "phi": phi,
        "sx": sx,
        "sy": sy,
        "sz": sz,
        "dy": dy,
        "gam": gam
        }

  def status(self):
    str = "** Goniometer Status **\n\t%10s\t%10s\t%10s\n" % ("Motor","User","Dial")                                                       
    keys = self.motors.keys()
    keys.sort()
    for key in keys:
       m = self.motors[key]
       str += "\t%10s\t%+10.4f\t%+10.4f\n" % (key,m.wm(),m.wm_dial())
    return str

  def detailed_status(self, toPrint=True):
    str = "** Goniomter Detailed Status **\n"
    keys = self.motors.keys()
    keys.sort()
    formatTitle = "%15s %20s  %18s  %4s  %10s  %10s  %10s  %10s  %10s  %10s  %7s  %7s  %7s  %7s  %5s  %5s  %7s\n"
    formatEntry = "%15s %20s  %18s  %4s  %10.4f  %10.4f  %10.4f  %10.4f  %10.4f  %10.4f  %7.1f  %7.1f  %7.1f  %7.1f  %5.1f  %5.1f  %7.1f\n"
    str += formatTitle % ("XCS Name", "EPICS Name", "PV Name", "EGU", "User", "User LL", "User HL", "Dial", "Dial LL", "Dial HL", "Vmin", "Vmin", "Vmax", "Vmax", "Accel", "Decel", "% Run")
    str += formatTitle % ("", "", "", "", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(EGU)", "(Rev/s)", "(EGU/s)", "(Rev/s)", "(EGU/s)", "(s)", "(s)", "Current")
    for key in keys:
       m = self.motors[key]
       str += formatEntry % (self.objName+"."+key,m.get_par("description"), m.pvname, m.get_par("units"), m.wm(), m.get_par("low_limit"), m.get_par("high_limit"), m.wm_dial(), m.get_par("dial_low_limit"), m.get_par("dial_high_limit"), m.get_par("s_base_speed"), m.get_par("base_speed"), m.get_par("s_speed"), m.get_par("slew_speed"), m.get_par("acceleration"), m.get_par("back_accel"), float(m.get_par("run_current",":")))
    if (toPrint):
      print str
    else:
      return str
       


  def __repr__(self):
    return self.status()

