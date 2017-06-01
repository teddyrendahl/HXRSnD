import pypslog
import pyca
import pypsepics
from utilities import estr
from utilitiesCalc import * 
from time import sleep

class LaserDelay:

  def __init__(self,name,stage,stage_pv,user_pv=None,):
    self.name = name
    self.stage_pv = stage_pv
    self.user_pv = user_pv
    self.stage = stage
   
  def set(self,t):
    """ Sets the stage delay 
        t is the desired laser delay (seconds)
    """
    mm=self.secondsToMM(t)
    self.stage(0.5*mm)
    sleep(0.1)
    self.set_pv() 
    return

  def set_pv(self):
    if self.user_pv==None:
      return
    t=self.getTime()
    pypsepics.put(self.user_pv,t)
    return
    
  def getTime(self):
    mm=pypsepics.get(self.stage_pv)
    t=self.mmToSeconds(2*mm)
    return t
 
  def mmToSeconds(self,mm):
    t=mm/u['mm']/c['c']
    return t

  def secondsToMM(self,t):
    mm=t*c['c']*u['mm']
    return mm
