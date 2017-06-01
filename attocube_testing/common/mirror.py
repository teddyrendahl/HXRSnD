import pypsepics
import utilities
import time
from numpy import *
from time import time, sleep
from utilitiesMotors import tweak, tweak2d

class Mirror(object):
  '''class that defines motorized mirror.
     Useage: __init__(self,motor_x,motor_y,step=0.01,dir_x=1,dir_y=1,name):
     functions : tweak() : 2D tweak of mirro
                 tweakx(): 1D tweak in x
                 tweaky(): 1D tweak in y
  '''
     
  def __init__(self,motor_x,motor_y,step=0.01,dir_x=1,dir_y=1,name='mirror'):
    self._name   = name
    self.mx = motor_x
    self.my = motor_y
    self._dirx = dir_x
    self._diry = dir_y
    self._step=step
    
  def tweak(self):
    tweak2d(self.mx,self.my,step=self._step,dirx=self._dirx,diry=self._diry)

  def tweakx(self):
    tweak(self.mx,step=self._step,dir=self._dirx)

  def tweaky(self):
    tweak(self.my,step=self._step,dir=self._diry)
    

  
