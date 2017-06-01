### Bob Nagler, Februari 2012. only really controls the motor movement

from utilities import estr
from utilitiesMotors import tweak2d
import pypsepics
from time import time,sleep
from mecbeamline import *
from utilities import estr
from flipper import Flipper

class RefLaser:
  def __init__(self,mirror):
    self.m=mirror
    self.air_x=mecmotors.ref_las_picoair_x
    self.air_y=mecmotors.ref_las_picoair_y
    self.vac_x=mecmotors.ref_las_picovac_x
    self.vac_y=mecmotors.ref_las_picovac_y
    self.flip1=Flipper("MEC:XT1:FLP:01","flip1")
    self._inpos=0
    self._outpos=-50.7
    self._motors_in_way=['yag2_yscreen','yag3_yscreen',
                         'ipm2_yd','ipm3_yd',
                         'ipm2_yt','ipm3_yt',
                         's1_d','s1_u','s1_s','s1_n',
                         's2_d','s2_u','s2_s','s2_n',
                         's3_d','s3_u','s3_s','s3_n',
                         'Be_ypos'
                         ]
    self._motors_outpos=[-52,-52,
                         0,0,
                         85,85,
                         -5,5,-5,5,
                         -5,5,-5,5,
                         -5,5,-5,5,
                         80]
    self._outpresetname = 'reflaser_beamline_position'

  def moveinBeamlineOut(self):
    self.movein()
    mecmotors.set_presets(self._motors_in_way, self._outpresetname, 'reference laser out position.')
    for motname,pos in zip(self._motors_in_way,self._motors_outpos):
      mecmotors.__dict__[motname].mv(pos)
      sleep(.1)
    mecvalves.glaswindow.close()
    self.unblock()   

  def moveoutBeamlineIn(self):
    self.moveout()
    print "Loading preset of previously saved \"beamline-in\" position..."
    mecmotors.move_to_preset(self._outpresetname,verbose=True,force=False)
    if mecvalves.glaswindow.openok():
      mecvalves.bewindow.close()
    else: print "Cannot open the glass window; no permission"
    self.block()


    
  def set_inpos(self,pos):
     self._inpos=pos
     
  def set_outpos(self,pos):
     self._outpos=pos
     
  def movein(self):
    self.m.move(self._inpos)

  def moveout(self):
    self.m.move(self._outpos)

  def wait(self):
    self.m.wait()

  def isin(self,pos=None):
    if pos is None:
      pos = self.m.wm()
    return ( abs(pos-self._inpos)<0.5 )

  def isout(self,pos=None):
    if pos is None:
      pos = self.m.wm()
    return ( abs(pos-self._outpos)<1.5 )

  def status(self):
    pos = self.m.wm()
    if self.isin(pos):
      pos_str =  estr("IN",color="red",type="normal")
    elif self.isout(pos):
      pos_str =  estr("OUT",color="green",type="normal")
    else:
      pos_str = estr("UNKOWN",color="red")
    str = "Ref laser position is : %s (stage at %.3f mm)" % (pos_str,pos)
    return str

  def block(self):
    self.flip1.flip_in()

  def unblock(self):
    self.flip1.flip_out()

  def tweakair(self):
    tweak2d(self.air_x,self.air_y,step=0.001,dirx=-1,diry=-1)

  def tweakvac(self):
    tweak2d(self.vac_x,self.vac_y,step=0.001,dirx=-1,diry=-1)

  def __repr__(self):
    return self.status()
