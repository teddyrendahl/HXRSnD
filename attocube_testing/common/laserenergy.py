#NOT USED BY MEC, OLD XPP file

import pypslog
import pyca
import pypsepics
from utilities import estr
from utilitiesCalc import * 
from time import sleep

class LaserEnergy:

  def __init__(self,name,wp_motor,wp_pv,user_pv=None,shg=0,leakage_pv=None,E0_pv=None):
    self.name = name
    self.wp_pv = wp_pv
    self.user_pv = user_pv
    self.leakage_pv = leakage_pv
    self.E0_pv = E0_pv
    self.wp_motor = wp_motor
    self.shg = shg
   
  def status(self):
    E=self.getE()
    E0=self.get_E0()
    leakage=self.get_leakage()
    wp=pypsepics.get(self.wp_pv)
    if self.shg:
      state=estr("400 nm",color='blue',type='normal')
    else:
      state=estr("800 nm",color='red',type='normal')
    str ="  %s: %4.4f\n" % (self.name,E)
    str +="      State: %s\n" % state
    str +="  Waveplate: %3.2f deg\n" % wp
    str +="         E0: %3.4f \n" % E0
    str +="    Leakage: %3.4f \n" % leakage
    return str

  def set(self,E):
    """ Sets the laser energy
        E is the desired laser energy (in either Joules or nomralized units
    """
    leakage=self.get_leakage()
    E0=self.get_E0()
    if E<leakage:
      str="Warning: desiried value %3.4f is less than %3.4f leakage, setting wp to 0" % (E,leakage)
      self.wp_motor(0)
      E=self.getE()
      sleep(0.1)
      self.set_pv()
      print str
      return 
    if E>E0:
      str="Warning: desiried value %3.4f is greater than the %3.4f availible energy, aborting" % (E,E0)
      print str
      return
    if self.shg:
      return
    else:
      theta=0.5*asind(((E-leakage)/(E0-leakage))**0.5)
      self.wp_motor(theta)
      sleep(0.1)
      self.set_pv() 
      return

  def __repr__(self):
    return self.status()
  
  def __call_(self,value):
    """ Shortcut for setting the E, for example: laserE(0.5) """
    self.set(value)

  def get_leakage(self):
    """ Returns the leakage value """
    return pypsepics.get(self.leakage_pv)

  def set_leakage(self,leakage):
    """ Sets the leakage value """
    pypsepics.put(self.leakage_pv,leakage)
    sleep(0.1)
    self.set_pv()
    return 
 
  def get_E0(self):
    """ Returns the E0 value """
    return pypsepics.get(self.E0_pv)

  def set_E0(self,E0):
    """ Sets the E0 value """
    pypsepics.put(self.E0_pv,E0)
    sleep(0.1)
    self.set_pv()
    return 
 
  def set_pv(self):
    if self.user_pv==None:
      return
    E=self.getE()
    pypsepics.put(self.user_pv,E)
    return
    
  def getE(self):
    wp=pypsepics.get(self.wp_pv)
    E0=self.get_E0()
    leakage=self.get_leakage()
    if self.shg:
      return
    else:
      E=(E0-leakage)*(sind(2*wp))**2+leakage
      return E
 
    
