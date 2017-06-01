import pypslog
import pyca
import pypsepics
from utilities import estr

class Illuminator:

  def __init__(self,name,pv_OnOff,pv_Volt,Vlow,Vhigh):
    self.name = name
    self.pv_OnOff = pv_OnOff
    self.pv_Volt = pv_Volt
    self.Vhigh = Vhigh
    self.Vlow = Vlow
  
  def status(self):
    volt=pypsepics.get(self.pv_Volt)
    onoff=pypsepics.get(self.pv_OnOff)
    if onoff==0:
      sstatus=estr("On",color='green',type='bold')
    elif  onoff==1:
      sstatus=estr("Off",color='red',type='bold')
    else:
      sstatus=estr("Not Known",color='white',type='normal')
    str1 ="%s:" % self.name
    str2 =" %s\n" % sstatus
    str3 ="Level:"
    str4 =" %d%%" % (self.level()*100)
    str = str1.rjust(10)+str2.ljust(5)+str3.rjust(10)+str4.ljust(5)
    return str

  def on(self):
    """ switches illuminator on """
    pypsepics.put(self.pv_OnOff,0)

  def off(self):
    """ switches illuminator off """
    pypsepics.put(self.pv_OnOff,1)

  def switch(self):
    """ switches illuminator """
    onoff = pypsepics.get(self.pv_OnOff)
    if onoff==1:
      pypsepics.put(self.pv_OnOff,1)
    elif onoff==0:
      pypsepics.put(self.pv_OnOff,0)
  
  def level(self,level='status'):
    """changes illumination level"""
    if level is "status":
	volt=pypsepics.get(self.pv_Volt)
	level = (volt-self.Vlow)/(self.Vhigh-self.Vlow)
	return level
    else:
      level = float(level)
      if level>1:
        level = level/100.
	print 'Illuminator Level was interpreted as percent'
      levelinvolt = self.Vlow + level*(self.Vhigh-self.Vlow)
      pypsepics.put(self.pv_Volt,levelinvolt)

  def info(self):
    """ Prints information about the lluminator """
    str="\n    %s\n" % (self.status())
    str += "           PV: %s\n" % self.pv
    str += " High Voltage: %4.3f Volts\n" % self.Vhigh
    str += "  Low Voltage: %4.3f Volts\n" % self.Vlow
    print str

  def __repr__(self):
    return self.status()
