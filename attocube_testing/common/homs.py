#!/usr/bin/python
# This module provides support 
#Homs for M3H beamline
# 
# Author:         Bob Nagler (SLAC)
# Created:        February, 2012
# Modifications:
#   February, 2012 MC
#       first version

from utilities import estr
import pypsepics
import time

class Homs:
    """ Class that controls two motors of the HOMS, encoders not yet implemented"""

    def __init__(self,homs_x,homs_a,pv_inpos_angle_encoder,pv_inpos_x,pv_angle_encoder,desc):
        self.x=homs_x
        self.angle=homs_a
        self._out=0.0
        self._in=-22
        self.__desc=desc
        self._pv_inpos_angle_encoder=pv_inpos_angle_encoder
        self._pv_inpos_x=pv_inpos_x
        self._pv_angle_encoder=pv_angle_encoder

    def get_angle_encoder_in(self):
        '''gets the value of the encoder that corresponds to the in position of the angle'''
        return pypsepics.get(self._pv_inpos_angle_encoder)

    def monitor_angle_encoder(self):
        '''continuously monitor and print the angle encoder. stop with CTRL-C'''
        try:
          while True:
              print(self.get_angle_encoder())
              time.sleep(1)
        except KeyboardInterrupt:
            pass
        
    def set_angle_encoder_in(self,val):
        '''sets the passed value as the new in position for the angle encoder of the HOMS'''
        pypsepics.put(self._pv_inpos_angle_encoder,val)

    def get_x_in(self):
        '''gets the value of x that corresponds to the in position'''
        return pypsepics.get(self._pv_inpos_x)

    def set_x_in(self,val):
        '''sets the passed value as the new in position for the angle encoder of the HOMS'''
        pypsepics.put(self._pv_inpos_x,val)

    def get_angle_encoder(self):
        '''gets the value of the angle encoder of the homs'''
        return pypsepics.get(self._pv_angle_encoder)

    def define_in_position(self):
        '''defines the current position of the homs as the new IN position'''
        self.set_x_in(self.x.wm())
        self.set_angle_encoder_in(self.get_angle_encoder())
        

#    def move_out(self):
#        ''' move the homs just out of the beam, assuming it is in now, which is 0.8mm'''
#        self.x.umv(0.8)
#        print "M3H is just out of the beampath "
     
    def park(self):
        self.x.umv(self._out)
        print self.status()
 
#    def move_in(self):
#        '''moves the Homs to the correct x position, and the does a few iterations to get the angle correct. Not yet very robust'''
#        self.x.umv(self.get_x_in())
#        time.sleep(3)
#        cor=0.02 # the stepsize in self.angle that needs to be made to correct 1 encoder error. This was empirically determined in nov 2012.
#        for i in (1,2,3,4):
#            self.angle.mvr(cor*(self.get_angle_encoder()-self.get_angle_encoder_in()))
#            time.sleep(3)
#        print 'if you are lucky, the homs is now in and aligned'

    def is_in(self):
        return(abs(self._in - self.x.wm())<0.8)

    def is_parked(self):
        limsw=self.x.check_limit_switches()
        return(limsw[0]=='high')

    def status(self):
        homsstat=self.__desc + " is "
        if self.is_in():
            homsstat+=estr("IN",color="yellow",type="normal")
            a_enc=self.get_angle_encoder()
            homsstat+=" (angle encoder = "+str(a_enc)+")"
        elif self.is_parked():
            homsstat+=estr("PARKED",color="green",type="normal")
        else:
            homsstat+="in "
            homsstat+=estr("UNKNOWN position",color="red",type="normal")

        
        return homsstat
