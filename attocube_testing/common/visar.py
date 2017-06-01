# Bob Nagler, (c) Feb 2013
# All units are SI

from numpy import *
from utilities import estr

class VISAR():
    """ Class that defines a visar bed.

        Calculates VPF, translation distances, etalons, etc.
        All SI units, except in the status where they are printed with units.
        usage: bed1=VISAR(etalon_thickness) ; see __init__ for more options.
        functions: bed1.d() : returns correct translation distance, in m
                   bed1.delay() : returs delay between arm, in s
                   bed1.vfp0() : returns velocity per finge, in m/s
                   bed1.stage_pos(): returns the correct stage position for the etalon used
                   bed1.status() : prints the status; distances in mm, wavelength in nm, other in SI
                   
    
    """
    def __init__(self,motor=None,block_arm_flipper=None,white_light_flipper=None,camera=None,slit_camera=None,etalon_h=None,z_t0=None,landa=532e-9,n=1.46071,delta=0.0318, theta=11.31):
        """ Initializes visar bed.

            etalon_h : etalon thickness
            z_t0: position of stage that gives the white light fringes
            landa : wavelength. Standard for mec visar is 532nm
            n : index of refraction at landa. Standard at MEC is 1.46071 (UVFS)
            delta : chromatic dispersion. Standard at MEC is 0.0318 (UVFS)
            theta: angle (in degrees) of beams on visar. At MEC this is 11.31degrees

        """

        self._h=etalon_h
        self._z_t0=z_t0
        self._landa=landa
        self._n=n
        self._delta=delta
        self._theta=theta/180.0*pi  # put theta in radians
        self._c=299792458 #speed of light in m/s
        self.m=motor #motor of the translation stage in interferometer
        self.cam=camera # camera of the visar output
        self.cam_slit=slit_camera
        self.block_arm_flipper=block_arm_flipper
        self.white_light_flipper=white_light_flipper
        

    def __call__(self):
        self.status()

    def d(self):
        """ Returns the translation of the visar bed that matches the etalon thickness h."""
        d0=self._h*(1-1/self._n)
        angle_correction=1.0/(cos(arcsin(sin(self._theta/2.0)/self._n))) #Correction factor: non-normal incidence
        return d0*angle_correction

    def delay(self):
        """ Returns the temporal delay between the two arms of the interferometer."""
        t0=2*self._h*(self._n-1/self._n)/self._c
        angle_correction=1.0/(cos(arcsin(sin(self._theta/2.0)/self._n))) #Correction factor: non-normal incidence
        return t0*angle_correction

    def vpf0(self):
        """Returns the Velocity Per Fringe of the visar. Uncorrected for windows or fast lens"""
        tau=self.delay()
        return self._landa/(2*tau*(1+self._delta))

    def stage_pos(self):
        """Returns the correct position of the visar stage, for the etalon used."""
        if self._z_t0==None: return None
        else: return self._z_t0+self.d()

    def go_zero_delay(self):
        """ Moves the stage to where there are white light fringes. """
        if self.m==None:print("no motor defined")
        else: self.m.mv(self._z_t0*1000.0)

    def go_stage_position(self):
        """moves the stage to where it needs to go for the current etalon"""
        if self.m==None:print("no motor defined")
        else: self.m.mv(self.stage_pos()*1000.0)

    def status(self):
        """Prints out an overview of the VISAR bed."""
        transdis_mm=self.d()*1000.0
        etalon_mm=self._h*1000.0
        if self._z_t0!=None:
            stage_pos_mm=self.stage_pos()*1000.0
            wl_mm=self._z_t0*1000.0
        else:
            stage_pos_mm=None
            wl_mm=None
        laserwavelength_nm=self._landa*1e9
        
        statstr= "laser wavelength : %.3f nm\n" %laserwavelength_nm
        if wl_mm!=None:statstr+= "White light stage reading : %.3f mm\n" %wl_mm
        statstr+="Etalon thickness : %.3f mm\n" %etalon_mm
        statstr+="Etalon material : n="+str(self._n)+" , delta="+str(self._delta)+"\n"
        statstr+="Correct translation distance : %.3f mm\n" %transdis_mm
        if stage_pos_mm!=None: statstr+="Correct stage position : %.3f mm\n" %stage_pos_mm
        if self.m==None:statstr+="no motor etalon motor defined"
        else:
          if abs(stage_pos_mm-self.m())<0.002: statstr+=estr("Stage in position\n",color="green",type="normal")
          else : statstr+=estr("Stage NOT in position\n", color="red",type="bold")
        statstr+="Velocity Per Fringe : "+str(self.vpf0())+" m/s\n"
        print statstr

    def calc_h(self,vpf):
        """Calculates the etalon distance required for the passed velocity per fringe"""

        tau_req=self._landa/(2*vpf*(1+self._delta))
        angle_correction=cos(arcsin(sin(self._theta/2.0)/self._n))
        h_req=tau_req*self._c*angle_correction/(2*(self._n-1/self._n))
        return h_req
