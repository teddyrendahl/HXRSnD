#!/usr/bin/python
# This module provides support 
# IPM (intensity position monitor) devices
# for the XPP beamline (@LCLS)
# 
# Author:         Bob Nagler (SLAC)
# Created:        February, 2012
# Modifications:
#   February, 2012 MC
#       first version

from common.utilities import estr
from common.utilitiesBeLenses import *
from common import linac
from common import config
import time

lcls_linac=linac.Linac()

class BeLens:
    """ Class that controls the Be compound refractive focussing system"""
    def __init__(self,mot_x,mot_y,mot_z,lens_set_file=config.DEFAULT_LENS_SET,fwhm_unfoc=800e-6,desc="MEC Be Lens System"):
        self.x=mot_x
        self.y=mot_y
        self.z=mot_z
        set1=getLensSet(1,lens_set_file)
        set2=getLensSet(2,lens_set_file)
        set3=getLensSet(3,lens_set_file)
        self._zlimhigh=-3819
        self._zlimlow=-4338
        self._sets=(set1,set2,set3)
        # will remove the hardcoded number but fetch from user PVs, zhou
        self._setposx=(0.385,0.31,0.26) # hardcoded belens position set 1->2->3
        self._setposy=(0.618,27.278,54.0) # hardcoded belens position set 1->2->3
        self._out=80
        self.__desc=desc
        self._fwhm_unfocused=fwhm_unfoc

        
    def out(self):
        '''Moves the be lenses out.'''
        self.y.move(self._out)

        
    def set_in(self,setnumber):
        if ( (setnumber<1) or (setnumber>3) ):
            print "select set 1-3"
            return
        print "moving motor `%s` to target #%d (pos = %f)" % (
        self.y.name,setnumber, self._setposy[setnumber-1])
        self.y.move(self._setposy[setnumber-1])
        print "\n and moving motor `%s` to target #%d (pos = %f)" % (
        self.x.name,setnumber, self._setposx[setnumber-1])
        self.x.move(self._setposx[setnumber-1])
        

    def is_in(self):
        """ check wether a stack is in, or wether lenses are out. otherwise returns UNKNOWN"""
        tolerance=1
        if (self._setposy[0]-tolerance<self.y.wm()<self._setposy[0]+tolerance):
            return 1
        elif (self._setposy[1]-tolerance<self.y.wm()<self._setposy[1]+tolerance):
            return 2
        elif (self._setposy[2]-tolerance<self.y.wm()<self._setposy[2]+tolerance):
            return 3
        elif (self._out-2<self.y.wm()<self._out+2):
            return "OUT"
        else:
            return "UNKNOWN position"
        

    def focus(self,printsummary=True):
        '''Moves the z position of the Belens to go to the focal position'''
        Ekev=lcls_linac.getXrayeV()/1000.0
        lsin=self.is_in()
        if lsin in (1,2,3):
           zn=-calcFocalLength(Ekev,lsin)*1000.0
           self.z.umv(zn)
        else: print "No lens set is in"

    

    def diameter(self,lens_set=None):
        ''' gives the smallest diameter of the lens set (1, 2 or 3)  that is passed '''   
        if lens_set==None: lens_set=self.is_in()
        if lens_set in (1,2,3):
            min_rad_curv=min(self._sets[lens_set-1])
##gets the minimum of lens set definition. so (1,.0005, 4,0.001) would give 0.0005, which is what we want, although it's a bit of a hack since the number of lenses is also taken into account to find the minimum; but since we won't put in lenses with a 1m radius of curvature, this will always work
            return 2*calcLensApertureRadius(min_rad_curv)
        else: return "No lens is in"
        

    def transmission(self,printsummary=True):
        '''returns an estimate of the transmission of the Be lenses, taking into account both the clipping and the
           attenuation, using the FWHM at the lens as the size for clipping. This is currently still a bit of a problem,
           since this FWHM is currently in most cases set to be less than the incoming beam, but comparable to the lens
           aperture such that we have better estimate of the focal spot.
        '''
        Ekev=lcls_linac.getXrayeV()/1000.0
        lenssetin=self.is_in()
        if lenssetin in (1,2,3):
            transmis=calcTransLensSet(Ekev,lenssetin,fwhm_unfocused=self._fwhm_unfocused)
        else: transmis=1.0
        if printsummary: print 'Transmission : ' +str(transmis)
        return transmis

    
            
    def spotsize(self,printsummary=True,fwhm_unfocused=800e-6):
        '''returns the spotsize at the center of the MEC vacuum chamber of the x-ray beam.

           The program uses gaussian beam optics. FWHM at the lens is taken to be the minimum
           of the fwhm_unfocussed beam and the diameter of the lens.'''
        Ex=lcls_linac.getXrayeV()/1000.0
        lenssetnumber=self.is_in()
        distance=-self.z.wm()/1000.0

        fwhm_lens=min(self.diameter(),self._fwhm_unfocused)
        
        if printsummary:
           print "distance lens to chamber center %s" %distance
        if lenssetnumber in (1,2,3):
           return calcBeamFWHM(Ex,self._sets[lenssetnumber-1],distance,printsummary=printsummary,fwhm_unfocused=fwhm_lens)
        else:
            print "no lens in beam"
            
            
            
    def setspotsizepre(self,spotsizefwhm):
        '''Moves the z-stage of the Be lens such that the beam has the passsed spotsize at the vacuum target
           center. The focus is behind TCC.

           The fwhm at the lens is taken to be the minimum
           of the fwhm_unfocussed beam and the diameter of the lens.
        '''
        
        Ex=lcls_linac.getXrayeV()/1000.0
        lenssetnumber=self.is_in()
        if lenssetnumber not in (1,2,3):
            print "no lens in beam"
        else:
            fwhm_lens=min(self.diameter(),self._fwhm_unfocused)
            zpos=findZpos(Ex,self._sets[lenssetnumber-1],spotsizefwhm,fwhm_unfocused=fwhm_lens)
            zpospre=-1000*zpos[0]
            zpospost=-1000*zpos[1]
            if self._zlimlow<zpospre<self._zlimhigh:
                self.z.move(zpospre)
                print "moving z motor of be lens to %f" % zpospre
            else:
                print "Cannot move motor to %f : motion out of range" %zpospre

                
            
    def setspotsizepost(self,spotsizefwhm):
        '''Moves the z-stage of the Be lens such that the beam has the passsed spotsize at the vacuum target
           center. The focus is before TCC.

           The fwhm at the lens is taken to be the minimum
           of the fwhm_unfocussed beam and the diameter of the lens.
        '''
        Ex=lcls_linac.getXrayeV()/1000.0
        lenssetnumber=self.is_in()
        if lenssetnumber not in (1,2,3):
            print "no lens in beam"
        else:
            fwhm_lens=min(self.diameter(),self._fwhm_unfocused)
            zpos=findZpos(Ex,self._sets[lenssetnumber-1],spotsizefwhm,fwhm_unfocused=fwhm_lens)
            zpospre=-1000*zpos[0]
            zpospost=-1000*zpos[1]
            if self._zlimlow<zpospost<self._zlimhigh:
                self.z.move(zpospost)
                print "moving z motor of be lens to %f" % zpospost        
            else:
                print "Cannot move motor to %f : motion out of range" %zpospost


            
    def status(self):
        '''returs a string of the status of the Be lens system'''
        lensin=self.is_in()
        if lensin in (1,2,3):
            spots=self.spotsize(printsummary=False)
            if spots < 1.5e-6: colour='green'
            else: colour='yellow'   
            str=estr("Lens stack %s is" %lensin,color="black",type="normal")
            str+=estr(" IN. ",color="yellow",type="normal")
            str+=estr("spotsize = %e " % spots,color=colour,type="bold")
            zpos=self.z.wm()
            str+=estr("(z position : %e" % zpos,color='black',type="normal")
            str+=estr("   FWHM at lens %e" %self._fwhm_unfocused, color='black',type='normal')
            str+=estr(" transmission : %e" %self.transmission(False), color='black',type='normal')
        elif lensin=="OUT":
            str=estr("Be Lenses are: ",color="black",type="normal")
            str+=estr("OUT.",color="green", type="normal")
        else:
            str=estr("Be Lenses are in: ",color="black" ,type="normal")
            str+=estr("UNKNOWN position. ",color="red",type="normal")
        return str
