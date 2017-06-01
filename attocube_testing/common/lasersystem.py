import pypsepics
import utilities
import os
from pypslog import logprint
from time import time,sleep



class LaserSystem:

  def __init__(self,system=6,beamline="mec"):
    self.system=system
    self.timeout=2000
    self.gainthresh=5000
    self.beamline=beamline
    self.__pvnames(self.system)


  def use_system(self,system):
    self.system=system
    self.__pvnames(self.system)
    self.__desired_value = None

  def __pvnames(self,system=None):
    if system is None: system = self.system
    self.__pv_angleshift="LAS:FS%d:Angle:Shift:Ramp:Target" % system
    self.__pv_angleshift_rbv="LAS:FS%d:REG:Angle:Shift:rd" % system
    self.__pv_switch_to_low_gain="LAS:FS%d:bt_low_gain_vcxo_loop" % system
    self.__pv_switch_to_high_gain="LAS:FS%d:bt_high_gain_vcxo_loop" % system
    self.__pv_lock="LAS:FS%d:bt_switch_to_this" % system
    self.__pv_gain="LAS:FS%d:REG:kp_vcxo:rd" % system
    self.__pv_locked="LAS:FS%d:locked" % system
    self.__pv_error="LAS:FS%d:alldiff_fs" % system
    self.__pv_diode_rf="LAS:FS%d:ACOU:amp_rf2_17_2:rd" % system
    if (self.beamline.lower() == "mec" ):
      self.__pv_angleshift_offset = "MEC:NOTE:LAS:FST0"
    else :
      self.__pv_angleshift_offset = None
    self._guilauncher=None

  def __call__(self,value=None):
    '''if instance is called with no atribute, it gives back or put the value inthe delay:
       usage: fstiming() : reads back current delay
              fstiming(value): puts value in delay
    '''
    return self.delay(value)


  def launch(self):
        """launches the gui viewer of the timing system"""
        if self._guilauncher==None : print('No gui file defined for this lasersystem')
        else : os.system(self._guilauncher)

  def relock(self):
    '''Tries to relock the fs laser'''
    pypsepics.put(self.__pv_lock,1)
    while (pypsepics.get(self.__pv_lock) == 1):
      sleep(1)
    
  def lowgain(self):
    '''Sets the gain of the feedback loop to the low value'''
    pypsepics.put(self.__pv_switch_to_low_gain,1)
    sleep(.2)
    pypsepics.put(self.__pv_switch_to_low_gain,0)

  def higain(self):
    '''Sets the gain of the feedback loop to the high value'''
    pypsepics.put(self.__pv_switch_to_high_gain,1)
    sleep(.2)
    pypsepics.put(self.__pv_switch_to_high_gain,0)

  def gain(self,value=None):
    ''' Reads or changes gain in the PD feedback loop
        usage:   gain(): reads back current gain
                 gain(value): sets gain to passed value
    '''
    if (value is None):
      return pypsepics.get(self.__pv_gain)
    else:
      pypsepics.put(self.__pv_gain,value)

  def error(self):
    '''gives the phase-locking error in s. this is indicative of the jitter between laser and X-rays'''
    return pypsepics.get(self.__pv_error)*1e-15
    
  def dial_delay(self,value=None):
    '''Reads or writes directly to the angle shift pv. This doesnt use the offsett.
       usage: dial_delay(): read pack the angle shift pv
              dial_delay(value): writes to the angle shift variable, and toggles gain to get new value fast.
    '''
    if (value is None):
      return pypsepics.get(self.__pv_angleshift_rbv)*1e-15
    else:
      #m = 0; M=14.7e-9
      m = 0; M=19.2e-9
      if ( (value<m) or (value>M) ):
        logprint("Phase shifter has a range (%.2e,%.2e), asked for %.3e, aborting" % (m,M,value),print_screen=True)
        return
      self.__desired_value = value
      if abs(pypsepics.get(self.__pv_angleshift_rbv)*1e-15-value)>5e-12:
        self.lowgain()
        pypsepics.put(self.__pv_angleshift,int(value*1e15))
        self.wait()
        self.higain()
      else:
        pypsepics.put(self.__pv_angleshift,int(value*1e15))
      return
      #return pypsepics.put(self.__pv_angleshift,int(value*1e15))

  def delay(self,value=None):
    ''' usage : delay(): gives the current delay of the x-rays with respect to the laser in seconds. 
                delay(value): sets the delay  of the x-rays with respect to the laser to the passed value.
                positive values mean the X-ray arrive after the laser
    '''
    if (self.__pv_angleshift_offset is not None):
      offset = pypsepics.get(self.__pv_angleshift_offset)
    else:
      offset = 0
    if (value is None):
      return -self.dial_delay()-offset
    else:
      return self.dial_delay( -(value+offset) )

  #def get_delay(self):
  #  return self.delay()

  
  def get_offset(self):
    return pypsepics.get(self.__pv_angleshift_offset) 

  #def move_delay(self,value):
  #  return self.delay(value)

  def set_delay(self,value):
    """Changes the offset such that the current value of the angle shift corresponds to the delay passed in 'value'
       useage: set_delay(value)"""
    if (self.__pv_angleshift_offset is None): return 0
    dial = self.dial_delay() 
    offset = - value - dial
    offset = pypsepics.put(self.__pv_angleshift_offset,offset)

  def redefine_delay(self,value=None):
    """Changes the offset such that the current value of the angle shift corresponds to the delay passed in 'value'
       useage: redefine_delay(value). If value is none, current angle shift will correspond to new zero delay, so
       redefine_delay() is equivalent to redefine_delay(0)"""
    if value==None: value=0
    self.set_delay(value)
    


  def wait(self):
    target = self.__desired_value
    t0=time()
    #print 'target is: %e; present delay is %e; Delta = %e' %(target,self.dial_delay(),self.dial_delay()-target)
    #print "cond1: %s; cond2: %s; cond3: %s." %(( abs(self.dial_delay()-target)>100e-15),  ((time()-t0)<self.timeout) , (self.gain()<self.gainthresh))
    while ( ( abs(self.dial_delay()-target)>100e-15) &  ((time()-t0)<self.timeout)):
      #print "cond1: %s; cond2: %s; cond3: %s." %(( abs(self.dial_delay()-target)>100e-15),  ((time()-t0)<self.timeout) , (self.gain()<self.gainthresh))
      sleep(0.01)

  def status(self):
    size = 25
    str = "%s: %s\n" % ("Laser system in use".rjust(size),self.system)
    delay = self.dial_delay()
    str+= "%s: %e (%s)\n" % ("current delay (s)".rjust(size),delay,utilities.time_to_text(delay))
    delay  = self.error()
    str+= "%s: %e (%s)\n" % ("current phase error (s)".rjust(size),delay,utilities.time_to_text(delay))
    gain = self.gain()
    if (gain ==0):
      gain_str="UNLOCKED"
    elif (gain <self.gainthresh):
      gain_str="LOW"
    else:
      gain_str="HIGH"
    str+="%s: %f (%s)\n" % ("gain".rjust(size),gain,gain_str)
    str+="%s: %d\n" % ("diode rf".rjust(size), pypsepics.get(self.__pv_diode_rf))
    return str

  def dial_delay_new(self,value=None):
    '''Seems to do exactly the same as dial_delay. Not sure what the difference is and cant be bothered now'''
    if (value is None):
      return pypsepics.get(self.__pv_angleshift_rbv)*1e-15
    else:
      #m = 0; M=14.7e-9
      m = 0; M=19.2e-9
      if ( (value<m) or (value>M) ):
        logprint("Phase shifter has a range (%.2e,%.2e), asked for %.3e, aborting" % (m,M,value),print_screen=True)
        return
      self.__desired_value = value
      if abs(pypsepics.get(self.__pv_angleshift_rbv)*1e-15-value)>5e-12:
        self.lowgain()
        pypsepics.put(self.__pv_angleshift,int(value*1e15))
        self.wait()
        self.higain()
      else:
        pypsepics.put(self.__pv_angleshift,int(value*1e15))
      return
      #return pypsepics.put(self.__pv_angleshift,int(value*1e15))

  def unlock(self):
    '''unlocks the feedback loop'''
    self.gain(0)


  def __repr__(self):
    return self.status()

  def is_locked(self):
    return pypsepics.get(self.__pv_locked)
