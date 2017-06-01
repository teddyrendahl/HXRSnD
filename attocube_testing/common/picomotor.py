import numpy
import pypsepics
import utilities
import sys,os,shutil
from pypslog import logprint
from time import sleep,time
from utilitiesMotors import estimatedTimeNeededForMotion,tweak
import datetime
import pprint,new
import simplejson
from functools import partial

class PicoMotor(object):
    """ PicoMotor module

        has only relative moves, and so no presets. For unsopported option (e.g. absolute moves
        it return 'not supported: picomotor'
    """
    def __init__(self,pvname,name=None,readbackpv="default"):
      self.__name__   = "mec picomotor class"
      self._pvname     = pvname
      if (name is None): name = pvname
      self._name       = name
      
      if (readbackpv is None):
        self.__readbackpv   = pvname
      elif (readbackpv == "default"):
        self.__readbackpv   = pvname + ".RBV"
      else:
        self.__readbackpv   = readbackpv
      self.__deadband=0.00001


    def home(self):
        print 'home not supported: picomotor'

    def wm(self):
        return pypsepics.get(self.__readbackpv)

    def stop(self):
        pypsepics.put(self._pvname+".STOP",1)
        print "stopping motor"

    def move(self,val):
        pypsepics.put(self._pvname,val)

    def mv(self,val):
        print("This is a picomotor; absolute moves not reliable. if you insist, you can use the move command")

    def wm_string(self):
        pos=self.wm()
        return str(pos)
    
    def mvr(self,val):
        beginpos=self.wm()
        endpos=beginpos+val
        self.move(endpos)

    def move_relative(self,val): self.mvr(val)

    def update_move_relative(self,howmuch,show_previous=True):
        pos = self.wm()
        self.update_move(pos+howmuch,show_previous)

    def umvr(self,howmuch,show_previous=True): self.update_move_relative(howmuch,show_previous)

    def update_move(self,value,show_previous=True):
        """ move motor to value while displaying motor position
            Crtl + C stops motor """
        if (show_previous):
          print "initial position: %s" % self.wm_string()
        self.move(value)
        sleep(0.02)
        try:
          while ( not self.__isthere() ):
            s = "motor position: %s" % self.wm_string()
            utilities.notice(s)
            sleep(0.01)
        except KeyboardInterrupt:
          print "Ctrl + C pressed. Stopping motor"
          self.stop()
          sleep(1)
        s = "motor position: %s" % self.wm_string()
        utilities.notice(s)
       

    def umv(self,value): self.update_move(value)

    def __isthere(self):
        deadband =self.__deadband
        usergoto = self.wm_desired_user()
        delta=abs(usergoto-self.wm())
        return  ( delta<10*deadband and not self.ismoving() )


    def wm_desired_user(self):
        return pypsepics.get(self._pvname)


    def ismoving(self):
      return (not pypsepics.get(self._pvname + ".DMOV"))

    def tweak(self,step=0.001,dir=1):
      tweak(self,step=step,dir=dir)
