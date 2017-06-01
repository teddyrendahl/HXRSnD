#!/usr/bin/python
# This module provides support 
# for the XPP CCM monochromator
# for the XPP beamline (@LCLS)
# 
# Author:         Marco Cammarata (SLAC)
# Created:        Aug 27, 2010
# Modifications:
#   Aug 27, 2010 MC
#       first version

import numpy as n
from numpy import rad2deg,arcsin,sqrt,tan,sin,pi
import sys
from utilities import estr
import pypsepics
from pypslog import logprint
from utilitiesCalc import tand

def rad2deg(thrad):
  thdeg=thrad/pi*180
  return thdeg

def deg2rad(thdeg):
  thrad=thdeg/180*pi
  return thrad

def lattconst(Element):
        dic = { 'Si':   5.431020504,
                        }
        d = dic[Element]
        return d

def dspacing(Element,reflection):
  (h,k,l)=(int(reflection[0]),int(reflection[1]),int(reflection[2]))
  return (lattconst(Element)/sqrt( (h**2+k**2+l**2) ) )


def E2lam(E):
        lam = 12.39842 /E
        return lam

def lam2E(l):
        E = 12.39842 /l
        return E

def getLomGeom(E,reflection):
#       (h,k,l)=(int(reflection[0]),int(reflection[1]),int(reflection[2]))
        th = arcsin(E2lam(float(E))/2/dspacing('Si',reflection))
        zm = 300/tan(2*th)
        thm=rad2deg(th)
        return thm, zm


def get220LomGeom(E):
        return getLomGeom(E,"220")

def get111LomGeom(E):
        return getLomGeom(E,"111")

class LOM:
  """ Class to control the XPP PIM """
  def __init__(self,z1,x1,y1,th1,ch1,h1n,h1p,th1f,ch1f,z2,x2,y2,th2,ch2,h2n,diode2,th2f,ch2f,dh,dv,dr,df,dd,yag_zoom):
    
    self._inh1n=None
    self._inx1=None
    self._outh1n=None
    self._outx1=None
    self._indiode=None
    self._outdiode=None
    self._outvert=None
    self._outhoriz=None
    self._indectris=None
    self._inyag=None
    self._outyag=None
    self._vslit_pos=None
    self._hslit_pos=None
    self._foils_pos=None
    self.z1   = z1
    self.x1   = x1
    self.y1   = y1
    self.th1   = th1
    self.chi1   = ch1
    self.h1n   = h1n
    self.h1p   = h1p
    self.th1f   = th1f
    self.chi1f   = ch1f

    self.z2   = z2
    self.x2   = x2
    self.y2   = y2
    self.th2   = th2
    self.chi2   = ch2
    self.h2n  = h2n
    self.diode2  = diode2
    self.th2f   = th2f
    self.chi2f   = ch2f

    self.dh   = dh
    self.dv   = dv
    self.dr   = dr
    self.df   = df
    self.dd   = dd
    self.yag_zoom   = yag_zoom
    self.E=None
    self.E1=None

  def __repr__(self):
    return self.status()

  def status(self):
    str  = self.info(toprint=0)
    str += "\n"
    str += self.tower1(toprint=0)
    str += "\n"
    str += self.tower2(toprint=0)
    str += "\n"
    str += self.tower3(toprint=0)
    return str

  def _list_isin(self,mot):
     isin='no'
     tol=mot.get_par("retry_deadband")
     pos=mot.wm()
     if mot==self.dh:
       inpos=self._hslit_pos
     elif mot==self.dv:
       inpos=self._vslit_pos
     elif mot==self.df:
       inpos=self._foils_pos
     for i,el in enumerate(inpos):
       if abs((pos-el))<tol:
          isin=i
     return isin

  def info(self,toprint=1):
    pre= "%s - " % estr("IN",type="normal")
    space=" "*3
    str  = estr("LODCM Status\n" ,color="white",type="bold")
    tol_h1n=2*self.h1n.get_par("retry_deadband")
    tol_x1=2*self.x1.get_par("retry_deadband")
    pos_h1n = self.h1n.wm()
    pos_x1 = self.x1.wm()
    if ((abs(pos_h1n-self._inh1n)<=tol_h1n) & (abs(pos_x1-self._inx1)<=tol_x1)):
      str += "crystal 1 is %s\n" % estr("IN",type="normal")
    elif ((abs(pos_h1n-self._outh1n)<=tol_h1n)|(abs(pos_x1-self._outx1)<=tol_x1)):
      str += "crystal 1 is %s\n" % estr("OUT",color='green')
       
    
    str += "%sEnergy 1st crystal = \t %.4f keV\n" % (space,self.getE1())
    str += "%sEnergy 2nd crystal = \t %.4f keV\n" % (space,self.getE2())
# Check for horizontal elements on the diagnostic tower
    pos=self.dh.wm()
    tol=self.dh.get_par("retry_deadband")
    if abs(pos-self._outhoriz)<=tol:
       str+= "%sHorizontal elements status:\t %s\n" % (space,estr("OUT",color="green"))
    else:
       str+= "%sHorizontal elements status:\t " % space
       tol=3. #for the dectris
       hslit_i=self._list_isin(self.dh)
       if abs(pos-self._indectris)<=tol:
         str+=pre
         str += "Dectris \n"
       elif hslit_i==0: 
         str+=pre
         str += "Slit 1 (100 micron)\n"
       elif hslit_i==1: 
         str+=pre
         str += "Slit 2 (500 micron) \n"
       elif hslit_i==2: 
         str+=pre
         str += "Slit 3 (1 mm) \n"
       else:
         str += "%s\n" % estr("Unkown position",type="normal")
# Check for vertical elements on the diagnostic tower
    pos=self.dv.wm()
    tol=self.dv.get_par("retry_deadband")
    if abs(pos-self._outvert)<=tol:
       str+= "%sVertical elements status:\t %s\n" % (space,estr("OUT",color="green"))
    else:
       str+= "%sVertical elements status:\t "  % space
       vslit_i=self._list_isin(self.dv)
       if abs(pos-self._inyag)<=tol:
         str+=pre
         str += "Yag-mono \n"
       elif vslit_i==0: 
         str+=pre
         str += "Slit 1 (100 micron) \n"
       elif vslit_i==1: 
         str+=pre
         str += "Slit 2 (500 micron) \n"
       elif vslit_i==2: 
         str+=pre
         str += "Slit 3 (1 mm) \n"
       else:
         str += "%s\n" % estr("Unkown position",type="normal")
#Check for calibration foils    
    foils={0:'Out',1:'Mo',2:'Zr',3:'Ge',4:'Cu',5:'Ni',6:'Fe',7:'Ti'}
    foils_i=self._list_isin(self.df)
    if foils_i=='no':
       str+= "%sCalibration foils status:\t %s\n%s" % (space,estr("Unknown position",type="normal"),space)
    elif foils_i==0:
       str+= "%sCalibration foils status:\t %s\n%s" % (space,estr("OUT",color="green"),space)
    else:
       foil=foils[foils_i]
       str+= "%sCalibration foils status:\t %s - %s\n%s" % (space,estr("IN",type="normal"),foil,space)
    pos=self.dd.wm()
    tol=self.dd.get_par("retry_deadband")
    if abs(pos-self._outdiode)<=tol:
       str+= "Diode 1 status:\t\t %s\n" % (estr("OUT",color="green"))
    elif abs(pos-self._indiode)<=tol:
       str+= "Diode 1 status:\t\t %s\n" % (estr("IN",type="normal"))
    else:
       str+= "Diode 1 status:\t\t %s\n" % (estr("Unknown position",type="normal"))
    if toprint:
      print str
    else:
      return str

  def tower1(self,toprint=1):
    str  = "** Tower 1 (crystal 1) **\n"
    str += "  (x,y,z,hn,hp) [user]: %+.4f,%+.4f,%+.4f,%+.4f,%+.4f\n" % (self.x1.wm(),self.y1.wm(),self.z1.wm(),self.h1n.wm(),self.h1p.wm())
    str += "  (x,y,z,hn,hp) [dial]: %+.4f,%+.4f,%+.4f,%+.4f,%+.4f\n" % (self.x1.wm_dial(),self.y1.wm_dial(),self.z1.wm_dial(),self.h1n.wm_dial(),self.h1p.wm_dial())
    str += "  (th,ch) [user]: %+.4f,%+.4f\n" % (self.th1.wm(),self.chi1.wm())
    str += "  (th,ch) [dial]: %+.4f,%+.4f\n" % (self.th1.wm_dial(),self.chi1.wm_dial())
    if (toprint):
      print str
    else:
      return str

  def tower2(self,toprint=1):
    str = "** Tower 2 (crystal 2) **\n"
    str += "  (x,y,z,hn) [user]: %+.4f,%+.4f,%+.4f,%+.4f\n" % (self.x2.wm(),self.y2.wm(),self.z2.wm(),self.h2n.wm())
    str += "  (x,y,z,hn) [dial]: %+.4f,%+.4f,%+.4f,%+.4f\n" % (self.x2.wm_dial(),self.y2.wm_dial(),self.z2.wm_dial(),self.h2n.wm_dial())
    str += "  (th,ch) [user]: %+.4f,%+.4f\n" % (self.th2.wm(),self.chi2.wm())
    str += "  (th,ch) [dial]: %+.4f,%+.4f\n" % (self.th2.wm_dial(),self.chi2.wm_dial())
    if (toprint):
      print str
    else:
      return str

  def tower3(self,toprint=1):
    str = "** Tower 3 (diagnostic) **\n"
    str += "  (h,v,r) [user]: %+.4f,%+.4f,%+.4f\n" % (self.dh.wm(),self.dv.wm(),self.dr.wm())
    str += "  (h,v,r) [dial]: %+.4f,%+.4f,%+.4f\n" % (self.dh.wm_dial(),self.dv.wm_dial(),self.dr.wm_dial())
    str += "  (pips,filter) [user]: %+.4f,%+.4f\n" % (self.dd.wm(),self.df.wm())
    str += "  (pips,filter) [dial]: %+.4f,%+.4f\n" % (self.dd.wm_dial(),self.df.wm_dial())
    if (toprint):
      print str
    else:
      return str

  def set_inpos(self,inh1n,inx1):
    self._inh1n=inh1n
    self._inx1=inx1
  def set_outpos(self,outh1n,outx1):
    self._outh1n=outh1n
    self._outx1=outx1
  def set_diode_inpos(self,indiode):
    self._indiode=indiode
  def set_diode_outpos(self,outdiode):
    self._outdiode=outdiode
  def set_vertical_outpos(self,outvert):
    self._outvert=outvert
  def set_horizontal_outpos(self,outhoriz):
    self._outhoriz=outhoriz
  def set_dectris_inpos(self,indectris):
    self._indectris=indectris
  def set_yag_inpos(self,inyag):
    self._inyag=inyag
  def set_yag_outpos(self,outyag):
    self._outyag=outyag
  def set_vslit_pos(self,vslit_pos):
    self._vslit_pos=vslit_pos
  def set_hslit_pos(self,hslit_pos):
    self._hslit_pos=hslit_pos
  def set_foils_pos(self,foils_pos):
    self._foils_pos=foils_pos

  def moveout(self):
    self.h1n.mv(self._outh1n)
    self.x1.mv(self._outx1)
  def movein(self):
    self.h1n.mv(self._inh1n)
    self.x1.mv(self._inx1)

  def diodein(self):
    self.dd.mv(self._indiode)
  def diodeout(self):
    self.dd.mv(self._outdiode)
  def verticalout(self):
    self.dv.mv(self._outvert)
  def yagin(self):
    self.dv.mv(self._inyag)
  def yagout(self):
    self.dv.mv(self._outyag)
  def vslitin(self,n):
    if (n>0)&(n<4):
       self.dv.mv(self._vslit_pos[n-1])
       if n==1:        print "100 micron slit in" 
       if n==2:        print "500 micron slit in" 
       if n==3:        print "2 mm slit in" 
    else:
       print "allowed 1-3"
  def horizontalout(self):
    self.dh.mv(self._outhoriz)
  def dectrisin(self):
    self.dh.mv(self._indectris)
  def hslitin(self,n):
    if (n>0)&(n<4):
       self.dh.mv(self._hslit_pos[n-1])
       if n==1:        print "100 micron slit in" 
       if n==2:        print "500 micron slit in" 
       if n==3:        print "2 mm slit in" 
    else:
       print "allowed 1-3"
  def foilsout(self):
       self.df.mv(self._foils_pos[0])
  def foilsin(self,n):
    if (n>0)&(n<8):
       self.df.mv(self._foils_pos[n])
       if n==1:        print "Mo foil in" 
       if n==2:        print "Zr foil in" 
       if n==3:        print "Zn foil in" 
       if n==4:        print "Cu foil in" 
       if n==5:        print "Ni foil in" 
       if n==6:        print "Fe foil in" 
       if n==7:        print "Ti foil in" 
    else:
       print "allowed 1-7"

  def moveE1(self,E,reflection='111'):
    (th,z) = getLomGeom(E,reflection)
    self.th1.move_silent(th)
    self.dr.move_silent(2*th)
    self.z1.move_silent(-z)
  
  def getE1(self,reflection='111'):
    th = self.th1.wm()
    l  = 2*sin( deg2rad(th) ) *dspacing("Si",reflection)
    return lam2E(l)

  def waitE1(self):
    self.th1.wait()
    self.dr.wait()
    self.z1.wait()

  def moveE(self,E,reflection='111'):
    (th,z) = getLomGeom(E,reflection)
    self.th1.move_silent(th)
    self.th2.move_silent(th)
    self.dr.move_silent(2*th)
    self.z1.move_silent(-z)
    self.z2.move_silent(z)
 
  def tweakX(self,x):
    self.x2.move_relative(x) 
    th = self.th2.wm()
    z=x/tand(2*th)
    self.z2.move_relative(z) 

  def getE(self,reflection='111'):
    th = self.th1.wm()
    l  = 2*sin( deg2rad(th) ) *dspacing("Si",reflection)
    return lam2E(l)

  def waitE(self):
    self.th1.wait()
    self.th2.wait()
    self.dr.wait()
    self.z1.wait()
    self.z2.wait()
  
  def getE2(self,reflection='111'):
    th = self.th2.wm()
    l  = 2*sin( deg2rad(th) ) *dspacing("Si",reflection)
    return lam2E(l)

  def setT(self,E,reflection="111"):
    (th,z) = getLomGeom(E,reflection)
    self.th1.set(th)
    self.th2.set(th)
    self.z1.set(-z)
    self.z2.set(z)
