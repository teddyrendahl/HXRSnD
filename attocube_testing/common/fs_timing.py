### Bob Nagler, August 2012
### V2.0, Bob Nagler, November 2014
### All units are SI (except direct reads from motor pv, which are in mm)

import pypsepics
import KeyPress
import sys
from numpy import *
from time import sleep
from utilities import estr

class FS_Timing(object):
    ''' Class that allows changing the delay of the femto-second laser, and compersate a delay stage in the timetool to keep the signal there centered.

        This class does NOT interact with the EPICS phase locking system. Timing should not be changed with that electronic delay once t0 is determined 
        for each experiment, except when larger delays are required that the stage can handle.
        Keeping the timetool signal centered is accomplished by keeping the following relation between the timetool_motor and the delay_motor: 
           timetool_motor - delay_motor = _timetool_offset
 
        general usage:
        fstiming(1e-12)        : set the delay to 1 ps, by moving the delay stage. Moves the delay stage on the timetool to keep signal stationary.
        redefine_t0()          : set the current value of the delay stage motor as t0. From now on relative delay are defined with respect to this refence.
        redefine_timetool_t0() : run this when the timetool sygnal is centered in the white light spectrum. Set the time_tool_offset to the correct value.
    '''

    def __init__(self,delay_motor,high_lim=0.5e-9,low_lim=-0.5e-9,timetool_motor=None,delay_pv='MEC:NOTE:LAS:FSDELAY',offset_pv='MEC:NOTE:LAS:FST0',timetool_offset_pv='MEC:NOTE:DOUBLE:56',name='fstiming'):
        self._name=name
        self.delay_motor=delay_motor
        self._low_lim=low_lim
        self._high_lim=high_lim
        self.timetool_motor=timetool_motor
        self._delay_pv=delay_pv                     # PV only for monitoring purposes. Changing this value won't change the delay. 
                                                    # its value is never read by python, only written to
        self._offset_pv=offset_pv                   # PV for offset value of delay motor. when motor is put to this value, the delay is 0fs.
        self._timetool_offset_pv=timetool_offset_pv # PV for the offset value of the timetool.The difference of the timetool motor and 
                                                    # the delay motor should equal this value. This ensure there will be an edge centered 
                                                    # in the timetool signal.
        self._c=299792458.0                         # speed of light is m/s 
        

    def __call__(self,value=None):
        '''if instance is called with no atribute, it gives back or put the value inthe delay:
           usage: nstiming() : reads back current delay
                  nstiming(value): puts value in delay
        '''
        return self.delay(value)


    def __write_delay_to_pv(self,value):
        ''' Write tvalue to the PV of the delay
        '''
        pypsepics.put(self._delay_pv,value)

    def __get_offset(self):
        '''returns the value of the offset.

           The offset is the motor value on the delay stage that will result in 
           time delay calculation of 0 (i.e. put the delay motor at the offset value and 
           the delay() command will return 0)
        '''
        return pypsepics.get(self._offset_pv)

    def __set_offset(self,value):
        '''Writes the value to the PV that holds the offset value.
        
           The value is a motor position in mm. 
           The offset is the motor value on the delay stage that will result in 
           time delay calculation of 0 (i.e. put the delay motor at the offset value and 
           the delay() command will return 0) 
        '''
        pypsepics.put(self._offset_pv,value)

    def redefine_t0(self):
        '''Redefines the current position of the delay motor as t0.

           usage : fstiming.redefine_t0()
           
        '''
        
        self.__set_offset(self.delay_motor.wm())
        self.__write_delay_to_pv(0.0)
   
    def __get_tt_offset(self):
        ''' Reads the offset from the timetool pv '''
        return pypsepics.get(self._timetool_offset_pv)

    def __set_tt_offset(self,value):
        ''' write value to  the offset from the timetool pv '''
        return pypsepics.put(self._timetool_offset_pv,value)


    def redefine_timetool_t0(self):
        ''' Set the timetool offset to current value.

            This command should be run when the edge of the timetool is in the center of the spectrum.
            Subsequent motions of the timing with delay(), will then keep the timetool signal centered,
            since delay will alway keep the relation timetool_motor - delay_motor = timetool_offset
        '''

        new_offset=self.timetool_motor.wm() - self.delay_motor.wm()
        self.__set_tt_offset(new_offset)
        

    def delay(self,value=None):
        '''Returns or changes the delay.

           If no value is passed, the current delay is calculated and returned.
           If a value is passed, the delay is changed to that value.
        '''
        if value==None:
            dt_current=-2*(self.delay_motor.wm()-self.__get_offset())/1000.0/self._c  #factor of thousand since the motor values are in mm, not m
            self.__write_delay_to_pv(dt_current)
            return dt_current
 
        elif self._low_lim < value < self._high_lim:
            delay_motor_value=-(value*self._c*1000.0/2)+self.__get_offset()            
            self.delay_motor.mv(delay_motor_value)                             # set delay_motor to correct position for the delay    
            self.timetool_motor.mv(delay_motor_value+self.__get_tt_offset())   # adjust timetool motor for correct delay
            self.delay_motor.wait()
            self.timetool_motor.wait()       
            self.__write_delay_to_pv(value)                                    # waits for both motors to stop moving. 
        
        else: print 'delay outside of allowed range'

  

    def mvr(self,value=0):
        ''' changes the delay a relative mount of value'''
        old_delay=self.delay()
        new_delay=old_delay+value
        self.delay(new_delay)
        

    def status(self):
        '''return a string that formats the delay and t0 '''
        retstr='Femtosecond laser : '
        delay=self.delay()
               
        retstr+=estr('Delay = ' + str(delay) +'\n',color='black',type='normal')
        return retstr



    def tweak(self,step=0.1e-12,dir=1):
  
      help = "q = exit; up = step*2; down = step/2, left = neg dir, right = pos dir\n"
      help = help + "g = go to abs timing"
      print "tweaking the delay"
      #print "tweaking motor %s (pv=%s)" % (motor.name,motor.pvname)
      print "current delay :"+   str(self.delay())

      if dir != 1 and dir != -1:
        print("direction needs to be +1 or -1. setting dir to 1")
    
  
      step = float(step)
      oldstep = 0
      k=KeyPress.KeyPress()
      while (k.isq() is False):
        if (oldstep != step):
          print "stepsize: %f" % step
          sys.stdout.flush()
          oldstep = step
        k.waitkey()
        if ( k.isu() ):
          step = step*2.
        elif ( k.isd() ):
          step = step/2.
        elif ( k.isr() ):
          self.mvr(step)
          print self.status()
        elif ( k.isl() ):
          self.mvr(-step)
          print self.status()
        elif ( k.iskey("g") ):
          print "enter absolute position (char to abort go to)"
          sys.stdout.flush()
          v=sys.stdin.readline()
          try:
            v = float(v.strip())
            self.delay(v)
          except:
            print "value cannot be converted to float, exit go to mode ..."
            sys.stdout.flush()
        elif ( k.isq() ):
          break
        else:
          print help
      print self.status()

   
