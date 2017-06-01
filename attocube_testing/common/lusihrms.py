from numpy import tan,sin,pi
from periodictable import xsf
from utilities import estr

class HRMS:
  def __init__(self,m1r,m1y,m2r,m2y,linac,park_m1r=0.0,park_m1y=20.0,park_m2r=180.0,park_m2y=20.0):
    self.distance = 530.
    self.angle = None
    self.m1r=m1r
    self.m1y=m1y
    self.m2r=m2r
    self.m2y=m2y
    self._park_m1r=park_m1r
    self._park_m1y=park_m1y
    self._park_m2r=park_m2r
    self._park_m2y=park_m2y
    self.linac = linac
    self._length=0.2

  def get_angle(self):
    '''returns the average angle of both mirrors in degrees'''
    return (self.m1r.wm()+self.m2r.wm())/2.

  def calc_offset(self,angle):
    """ calculate beam vertical offset, angle in deg """
    return -tan(2*angle/180.*pi)*self.distance

  def offset(self):
    """ calculates the current offset, and returns it """
    return self.calc_offset(self.get_angle())

  def is_parked(self):
    """ checks wether the HRM is parked. Returns true if it is, false if not """
    if (-0.1<self.m1r.wm()-self._park_m1r<0.1) and (-0.1<self.m2r.wm()-self._park_m2r<0.1) and (-0.1<self.m1y.wm()-self._park_m1y<10.1) and (-0.1<self.m2y.wm()-self._park_m2y<0.1): return True
    else: return False
    

  def move(self,angle):
    '''
    useage: move(angle)
    moves the hrm to given angle (in degrees). Sets the offset to match the angle'''
    self.angle=angle
    self.m1r.move(angle)
    self.m2r.move(angle)
    self.m1y.move(0)
    offset = self.calc_offset(angle)
    self.m2y.move(offset)
    print "beam offset %.3f" % offset

  def status(self):
    
    if self.is_parked():
        out="HRM is %s" % estr("PARKED",color="green",type="normal")
    else:  
        angle=self.angle=self.get_angle()
        E=self.E=self.linac.getXrayeV()
        out  = "Harmonic Rejection Mirrors (HRMS)\n"
        out += "Angle       = %.3f deg (=%.3f mrad)\n" % (angle,angle/180.*3.14*1e3)
        out += "Beam offset = %.3f mm\n" % (self.calc_offset(angle))
        out += "Aperture  y = %.3f um\n"  % (1e6*self.aperture())
        out += "Beam energy = %.3f keV\n" % (self.E/1e3)
        out += "R(1st harm) = %.3e\n"    % self.getTforE(energy=E)
        out += "R(3rd harm) = %.3e\n"    % self.getTforE(energy=3*E)
    return out

  def getTforE(self,angle=None,energy=None):
    if (energy is None): energy=self.linac.getXrayeV()
    if (angle is None):
      if (self.angle is None): self.angle=self.get_angle()
      angle=self.angle
    r = xsf.mirror_reflectivity("Si",angle=angle,energy=energy/1e3)
    # r**2 because 2 mirrors
    return float(r*r)
    return r*r

  def __repr__(self):
    return self.status()

  def park(self):
    self.m1r.move(self._park_m1r)
    self.m2r.move(self._park_m2r)
    self.m1y.move(self._park_m1y)
    self.m2y.move(self._park_m2y)

 
  def aperture(self):
    '''returns the size of the aperture in y that the hrm cathes.'''
    return self._length*sin(self.get_angle()/180.0*pi)
