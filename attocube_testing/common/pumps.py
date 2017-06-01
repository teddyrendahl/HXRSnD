from utilities import estr
import pypsepics
from time import time,sleep


class DCBool:
  def __init__(self,pv,Vhigh=10,Vlow=0):
    self.pv=pv
    self.Vhigh=Vhigh
    self.Vlow=Vlow
  def high(self):
    pypsepics.put(self.pv,self.Vhigh)
  def low(self):
    pypsepics.put(self.pv,self.Vlow)
  def get(self):
    v=pypsepics.get(self.pv)
    b = 0
    if   ( abs( v - self.Vhigh ) < 0.1 ):
      b=1
    elif ( abs( v - self.Vlow  ) < 0.1 ):
      b=0
    else:
      b="?"
    return b

class DCPump:
  def __init__(self,speed_pv="XPP:R31:IOC:21:ao0:out8",speed_rbv=None,A="XPP:R31:IOC:21:ao0:out9",B="XPP:R31:IOC:21:ao0:out10"):
    self.speed_rbv=speed_rbv
    self.speed_pv=speed_pv
    self.A=DCBool(A)
    self.B=DCBool(B)

  def breaking(self):
    self.A.high()
    self.B.high()

  def poweroff(self):
    self.A.low()
    self.B.low()

  def forward(self):
    self.A.high()
    self.B.low()

  def reverse(self):
    self.A.low()
    self.B.high()

  def speed(self,value=None):
    if (value is not None):
      pypsepics.put(self.speed_pv,value)
    if (self.speed_rbv is None):
      s=pypsepics.get(self.speed_pv)
    else:
      s=pypsepics.get(self.speed_rbv)
    return s

  def status(self):
    print self.status_str()

  def status_str(self):
    a=self.A.get()
    b=self.A.get()
    s=self.speed()
    status = "????????"
    if ( (a =="?") or (b=="?") ):
      status = "????????"
    elif ( a & (not b) ):
      status = "pumping forward"
    elif (b &  (not a) ):
      status = "pumping backward"
    elif ( (not b) & (not a) ):
      status = "power off"
    elif ( a & b ):
      status = "breaking"
    str =  "## Pump ##\n"
    str += "   status: %s\n" % status
    str += "   current speed (set value): %f\n" % pypsepics.get(self.speed_pv)
    if (self.speed_rbv is not None):
      str += "   current speed (readback) : %f\n" % s
    return str

  def __repr__(self):
    return self.status_str()

pump=DCPump(speed_pv="XPP:R31:IOC:21:ao0:out8",A="XPP:R31:IOC:21:ao0:out9",B="XPP:R31:IOC:21:ao0:out10")
