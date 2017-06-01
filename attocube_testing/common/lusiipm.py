#!/usr/bin/python
# This module provides support 
# IPM (intensity position monitor) devices
# for the XPP beamline (@LCLS)
# 
# Author:         Marco Cammarata (SLAC)
# Created:        June 14, 2010
# Modifications:
#   June 14, 2010 MC
#       first version
#   2011-2012, modified for MEC by Bob Nagler

from utilities import estr
#from mecbeamline import hrm

class target:
  """ Class to define filter properties 
      Parameters are the motor that is controlling the
      target and an arrray of positions
      the array 0 is the out position
      the array 1 is the 1st target and so on
  """
  def __init__ (self,mot_target_y,target_pos,CCM_offset):
    self.ty    = mot_target_y
    self.targ_pos  = target_pos
    self.CCM_offset = CCM_offset
  def movein(self,num,ccm=False):
    """ move the target `num` in the beam
        does not wait for completion of movement.
        
    """
   
    
    if ( (num<1) or (num>4) ):
      print "select target 1-4"
      return
    if (ccm):
      print "moving motor `%s` to target #%d (pos = %f)" % (
        self.ty.name,
        num,
        self.targ_pos[num]+self.CCM_offset)
      self.ty.move(self.targ_pos[num]+self.CCM_offset)
    else:
      print "moving motor `%s` to target #%d (pos = %f)" % (
        self.ty.name,
        num,
        self.targ_pos[num])
      self.ty.move(self.targ_pos[num])
  def moveout(self):
    """ move the target out of the way
        does not wait for completion of movement"""
    print "moving motor `%s` to hole (pos = %f)" % (
        self.ty.name,
        self.targ_pos[0])
    self.ty.move(self.targ_pos[0])

  def status(self):
    pos = self.ty.wm()
    str=estr("UNKNOWN",color="red",type="normal")
    str += "target position (ty = %.4f)" % (pos)
    if (self.isout()):
      str = estr("target OUT",color="green",type="normal")
    (targ_in,isCCM) = self.isin()
    if (targ_in>0 and not isCCM):
      str = estr("Target %d "%targ_in ,color="yellow",type="normal")
      str+="(ty = %.4f)" % pos
    if (targ_in>0 and isCCM):
      str = "Target %d is IN (CCM position) (ty = %.4f)" % (targ_in,pos)
    return str

  def isin(self):
    pos = self.ty.wm()
    whichisin = None
    isCCM = None
    deadband = 2*self.ty.get_par("retry_deadband")
    for i in range(1,5):
      if (abs(pos-self.targ_pos[i])<deadband):
        whichisin = i
        isCCM = False
        break
    for i in range(1,5):
      if (abs(pos-self.targ_pos[i]-self.CCM_offset)<deadband):
        whichisin = i
        isCCM = True
        break
    return (whichisin,isCCM)

  def isout(self):
    """ return True if the filter is within 5um from 
        the predined `out` position"""
    return ( abs(self.ty.wm()-self.targ_pos[0])<5e-3 )
  def wait(self):
    """ wait for motor to stop moving (check done every 20ms) """
    return self.ty.wait()

class IPM:
  """ Class to control the MEC IPM """
  def __init__(self,mot_diode_x,mot_diode_y,mot_target_y,target_pos,det,desc="ipm"):
    self.dx = mot_diode_x
    self.dy = mot_diode_y
    self._CCM_offset = 7.55
    self._diodeout = -40
    self._diodein = 0
    self._targetpos=target_pos ##added, will his work?
    
    # target_pos[0] = out
    # target_pos[1] = target 1
    # target_pos[2] = target 2
    # target_pos[3] = target 3
    self.ty = mot_target_y
    self.__target = target(mot_target_y,target_pos,self._CCM_offset)
    self.__desc=desc
    self.__det=det
  def set_ccmoffset(self,offset):
    self._CCM_offset=offset
  def set_diodeout(self,pos):
    self._diodeout=pos
  def set_diodein(self,pos):
    self._diodein=pos
  def diode_out(self):
    self.dy.move(self._diodeout)
  def diode_in(self):
    self.dy.move(self._diodein)
  def target_in(self,num):
    self.__target.movein(num)
  def target_inccm(self,num):
    self.__target.movein(num,ccm=True)
  def target_out(self):
    self.__target.moveout()
  def __repr__(self):
    return self.status()
  def dis_in(self):
    return( -0.1<self.dy.wm()<0.1)
  def dis_out(self):
    return(self.dy>44.8)
  def status(self):
    if self.dis_in():
      dpos=estr("IN",color="yellow",type="normal")
    elif self.dis_out():
      dpos=estr("OUT",color="green",type="normal")
    else:
      dpos=estr("UNKNOWN",color="red", type="normal")
      
    str  = estr("%s" % self.__desc,color="black",type="bold")
    str+=" diode " + dpos
    str += " @ (dx,dy) = (%.4f,%.4f), " % (self.dx.wm(),self.dy.wm())
    str += " %s\n" % self.__target.status()
#    str += " %s" % self.__det.status()
    return str
 
