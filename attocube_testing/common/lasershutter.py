import pypslog
import pyca
import pypsepics
from utilities import estr

class LaserShutter:

  def __init__(self,name,pv,Vhigh,Vlow,tol=0.01):
    self.name = name
    self.pv = pv
    self.Vhigh = Vhigh
    self.Vlow = Vlow
    self.tol = tol
  
  def status(self):
    v=pypsepics.get(self.pv)
    if abs(v-self.Vhigh) < self.tol:
      sstatus=estr("Open",color='green',type='normal')
    elif abs(v-self.Vlow) < self.tol:
      sstatus=estr("Closed",color='red',type='normal')
    else:
      sstatus=estr("Not Known",color='white',type='normal')
    str1 ="%s:" % self.name
    str2 =" %s" % sstatus
    str = str1.rjust(10)+str2.ljust(10)
    return str

  def open(self):
    """ opens the shutter """
    pypsepics.put(self.pv,self.Vhigh)

  def close(self):
    """ closes the shutter """
    pypsepics.put(self.pv,self.Vlow)

  def info(self):
    """ Prints information about the shutter """
    str="\n    %s\n" % (self.status())
    str += "           PV: %s\n" % self.pv
    str += " Open Voltage: %4.3f Volts\n" % self.Vhigh
    str += "Close Voltage: %4.3f Volts\n" % self.Vlow
    str += "  Voltage Tol: %4.3f Volts\n" % self.tol
    print str

  def __repr__(self):
    return self.status()

