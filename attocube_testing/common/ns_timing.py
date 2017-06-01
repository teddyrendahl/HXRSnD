### Bob Nagler, August 2012
### All units are SI

import pypsepics
from numpy import *
from time import sleep
from utilities import estr

class NS_Timing(object):
    ''' Class that defines a timing channel of a DG645 delay generator.
        It uses an epics PV that is the value of the offset, so that timings
        can be given with respect to a reference. For example, the ns laser
        timing would be specified with respect to a t0, which is when the
        of the laser and the x-rays coincide.
        Since most users think of delaying the X-rays with respect to the
        laser, positive delays pull the laser trigger earlier.
        So:
        The offset is the value on the DG645 box that corresponds to zero delay
        The delay = offset - Value_on_DG645
        The delay is also written to an epics pv whenever it is written or read
    '''

    def __init__(self,channel_pvbase='MEC:LAS:DDG:03:e',high_lim=1.0,low_lim=0.0,offset_pv_name='MEC:NOTE:LAS:NST0',delay_pv_name=None,name='nstiming'):
        self._name=name
        self._pvbase=channel_pvbase
        self._low_lim=low_lim
        self._high_lim=high_lim
        self._offset_pv_name=offset_pv_name
        self._delay_pv_name=delay_pv_name #epics variable that hold the current delay. It is updated whenever a delay is written or read by .delay()

    def __call__(self,value=None):
        '''if instance is called with no atribute, it gives back or put the value inthe delay:
           usage: nstiming() : reads back current delay
                  nstiming(value): puts value in delay
        '''
        return self.delay(value)


    def get_offset(self):
        '''returns the value of the offset'''
        return pypsepics.get(self._offset_pv_name)

    def set_offset(self,value):
        '''writes the value to the PV that holds the offset value'''
        pypsepics.put(self._offset_pv_name,value)

    def wait(self):
        '''waits 0.1s, such that the DG645 is updated before continuing the script'''
        sleep(0.1)

    def dial_delay(self,value=None):
        '''return the current delay  if  value is None.
           If a value is passed, the delay is change to that value. All values in seconds.
           The returned values are those directly read of the DG645, without offset taken into
           account.
        '''

        if value==None:
            delay_read=pypsepics.get(self._pvbase+'DelaySI')
            return double(delay_read[5:])
        elif self._low_lim < value < self._high_lim:
            pypsepics.put(self._pvbase+'DelayAO',value)
        else: print('Delay outside of allowed range')

    def delay(self,value=None):
        '''return the current delay of the X-rays with respect to laser if  value is None.
           If a value is passed, the delay is change to that value. All values in seconds.
        '''
        if value==None:
            delay_value=self.get_offset() - self.dial_delay()
            if self._delay_pv_name!=None:
                pypsepics.put(self._delay_pv_name,delay_value)
            return delay_value
        else:
            self.dial_delay(self.get_offset() - value)
            if self._delay_pv_name!=None:
                pypsepics.put(self._delay_pv_name,value)

    def status(self):
        '''return a string that formats the delay and t0 '''
        retstr='Nanosecond laser : '
        delay=self.delay()
        if not (-5e-9 < delay < 50e-9):
            color='red'
            type='bold'
        else:
            color='black'
            type='normal'
        retstr+=estr('Delay = ' + str(delay) +'\n',color=color,type=type)
        retstr+=estr('                   T0 = ' + str(self.get_offset()) +'\n',color=color,type=type)
        return retstr

    def redefine_delay(self,value=0.0):
        '''redifine the current value of the delay generator as the delay given by
           the value. The value is standard 0.
           usage: redefine_delay(): the current setting of the delay generator correspond to t0
                  redefine_delay(4e-9): the current setting of the delay generator correspond to a delay of 4ns
        '''
        self.set_offset(self.dial_delay()+value)


    def mvr(self,value):
        """Moves the delay 'value' reltive the current delay"""
        old_delay=self.delay()
        new_delay=old_delay+value
        self.delay(new_delay)
