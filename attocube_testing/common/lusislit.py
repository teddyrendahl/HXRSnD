import numpy
import sys
from utilities import estr
from utilitiesMotors import tweak2d
import pypsepics
import time

class LusiSlit:
  """ Class to control the lusislit
      each slit object is defined by passing the four motor it is connected to.
      (up,down,north,south) plus an optional mnemonic name.
      The 4 motors are combined to provide an offset and gap.
      hg = N-S; ho = (N+S)/2
      vg = U-D; vo = (U+D)/2
      for each [hg,ho,vg,vo] methods are provided to retrieve the value (wm_*)
      move to a given value (mv_*) and set the current position as new value (set_*)
  """
  def __init__(self,u,d,n,s,name=""):
      self.u = u
      self.d = d
      self.n = n
      self.l = n
      self.s = s
      self.r = s
#      self.hg = None
#      self.vg = None
#      self.ho = None
#      self.vo = None
      self.upos = self.dpos = self.spos = self.npos = numpy.nan
      self.__name = name

  def __call__(self,hg,vg):
    self.mv_hg(hg)
    self.mv_vg(vg)

  def __repr__(self):
    return self.status()

#  def __getattr__(self,name):
#    if (name == "ho"):
#        return self.__wm_ho()
#    elif (name == "hg"):
#        return self.__wm_hg()
#    elif (name == "vo"):
#        return self.__wm_vo()
#    elif (name == "vg"):
#        return self.__wm_vg()
#    else:
#        return "the attribute '%s' does not exist" % (name)

  def __update(self):
    self.npos = self.n.wm()
    self.spos = self.s.wm()
    self.upos = self.u.wm()
    self.dpos = self.d.wm()

  
  def wm_ho(self,fast=False):
    if (not fast):  self.__update()
    return (self.npos+self.spos)/2
  def wm_hg(self,fast=False):
    if (not fast):  self.__update()
    return (self.npos-self.spos)
  def wm_vo(self,fast=False):
    if (not fast):  self.__update()
    return (self.upos+self.dpos)/2
  def wm_vg(self,fast=False):
    if (not fast):  self.__update()
    return (self.upos-self.dpos)

  def mv_ho(self,offset=0):
    gap = self.wm_hg()
    if (numpy.isnan(gap)):
      print "Problem in getting the current horizontal gap, stopping"
    else:
      self.s.move(offset-gap/2)
      self.n.move(offset+gap/2)

  def set_ho(self,newoffset=0):
    gap = self.wm_hg()
    if (numpy.isnan(gap)):
      print "Problem in getting the current horizontal gap, stopping"
    else:
      self.s.set(newoffset-gap/2)
      self.n.set(newoffset+gap/2)

  def mv_vo(self,offset=0):
    gap = self.wm_vg()
    if (numpy.isnan(gap)):
      print "Problem in getting the current vertical gap, stopping"
    else:
      self.u.move(offset+gap/2)
      self.d.move(offset-gap/2)

  def set_vo(self,newoffset=0):
    gap = self.wm_vg()
    if (numpy.isnan(gap)):
      print "Problem in getting the current vertical gap, stopping"
    else:
      self.d.set(newoffset-gap/2)
      self.u.set(newoffset+gap/2)

  def mv_hg(self,gap=None):
    if (gap is None):
        return
    gap = float(gap)
    offset = self.wm_ho()
    if (numpy.isnan(offset)):
      print "Problem in getting the current horizontal offset position, stopping"
    else:
      self.s.move(offset-gap/2)
      self.n.move(offset+gap/2)

  def set_hg(self,newgap=0):
    newgap = float(newgap)
    offset = self.wm_ho()
    if (numpy.isnan(offset)):
      print "Problem in getting the current horizontal offset position, stopping"
    else:
      self.s.set(offset-newgap/2)
      self.n.set(offset+newgap/2)

  def mv_vg(self,gap=None):
    if (gap is None):
        return
    gap = float(gap)
    offset = self.wm_vo()
    if (numpy.isnan(offset)):
      print "Problem in getting the current vertical offset position, stopping"
    else:
      self.d.move(offset-gap/2)
      self.u.move(offset+gap/2)

  def set_vg(self,newgap=0):
    newgap = float(newgap)
    offset = self.wm_vo()
    if (numpy.isnan(offset)):
      print "Problem in getting the current vertical offset position, stopping"
    else:
      self.d.set(offset-newgap/2)
      self.u.set(offset+newgap/2)

  def wait(self):
    self.d.wait()
    self.u.wait()
    self.s.wait()
    self.n.wait()

  def waith(self):
    self.s.wait()
    self.n.wait()

  def waitv(self):
    self.d.wait()
    self.u.wait()

  def open(self,sizegap=25):
    self.mv_vg(sizegap)
    self.mv_hg(sizegap)

  def isopen(self):
    return((self.wm_hg() >6) and (self.wm_vg()>6) and (-1<self.wm_vo()<1) and (-1<self.wm_ho()<1))

  def isclosed(self):
    return((self.wm_hg()<0) or (self.wm_vg()<0))
  
  def status(self):
    self.__update()
    out = "slit %s:" %self.__name
    if self.isopen():
      out+=estr(" OPEN  ",color="green",type="normal")
    elif self.isclosed():
      out+=estr(" CLOSED ",color="red", type="bold")
    else:
      out+=estr(" IN     ",color="yellow", type="normal")
    out+="(hg,vg) = (%+.4f x %+.4f); (ho,vo) = (%+.4f,%+.4f)" % (self.wm_hg(fast=True),self.wm_vg(fast=True),\
          self.wm_ho(fast=True),self.wm_vo(fast=True) )
    return out

  def tweakpos(self,val=0.1):
    '''Does a 2d tweak of the position of the slit'''
    tweak2d(self.mv_ho,self.mv_vo,val)

  def home(self):
    print "Start homing procedure now for slit %s:" % self.__name
    print "North blade : " , self.n.pvname
    print "South blade : " , self.s.pvname
    print "Top blade : "   , self.u.pvname
    print "Bottom blade : ", self.d.pvname
    pypsepics.put(self.n.pvname+'.HOMR',1) # move to low limit switch
    pypsepics.put(self.s.pvname+'.HOMF',1) # move to high limit switch
    pypsepics.put(self.u.pvname+'.HOMR',1) # move to low limit switch
    pypsepics.put(self.d.pvname+'.HOMF',1) # move to high limit switch

    for i in range(3):
      status_n = 0
      status_s = 0
      status_u = 0
      status_d = 0 
      while(True):
        time.sleep(3)
        status_n = pypsepics.get(self.n.pvname+'.LLS')
        time.sleep(3)
        status_s = pypsepics.get(self.s.pvname+'.HLS')
        time.sleep(3)
        status_u = pypsepics.get(self.u.pvname+'.LLS')
        time.sleep(3)
        status_d = pypsepics.get(self.d.pvname+'.HLS')
        if status_n == 1 and status_s == 1 and status_u == 1 and status_d == 1:
          break # everyone is on the limit siwtch right now

    print "everyone is on the limit siwtch right now"
    pypsepics.put(self.n.pvname+':ZERO_P.PROC',1) # set dial to zero
    pypsepics.put(self.s.pvname+':ZERO_P.PROC',1) # set dial to zero
    pypsepics.put(self.u.pvname+':ZERO_P.PROC',1) # set dial to zero
    pypsepics.put(self.d.pvname+':ZERO_P.PROC',1) # set dial to zero   

    time.sleep(2)

    # set the pre-defined offset for s1, s2 and s3
    if self.__name == 's1':
      pypsepics.put(self.n.pvname+'.OFF', -17.02)
      pypsepics.put(self.s.pvname+'.OFF', 15.52)
      pypsepics.put(self.u.pvname+'.OFF', -15.82)
      pypsepics.put(self.d.pvname+'.OFF', 16.334)
    elif self.__name == 's2':
      pypsepics.put(self.n.pvname+'.OFF', -17.04)
      pypsepics.put(self.s.pvname+'.OFF', 15.204)
      pypsepics.put(self.u.pvname+'.OFF', -16.75)
      pypsepics.put(self.d.pvname+'.OFF', 15.64)
    elif self.__name == 's3':
      pypsepics.put(self.n.pvname+'.OFF', -16.25)
      pypsepics.put(self.s.pvname+'.OFF', 14.4)
      pypsepics.put(self.u.pvname+'.OFF', -15.87)
      pypsepics.put(self.d.pvname+'.OFF', 16.692)
    else:
      print "Wrong slit name!"


    print "Done homing slit: %s" % self.__name
