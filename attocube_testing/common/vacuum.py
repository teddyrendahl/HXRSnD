import pypsepics
from utilities import estr
from pypslog import logprint

class Valve:
  """ 
  Valve class : Used to control and monitor valves
  Instances defined in xppbeamline.py
  Only works for now for normal gate valves. doesn't work on the electrical valves on the vent lines for example. Need to define a derived class for this.
  """  
  def __init__(self,pvname,name):
    self.pvname=pvname
    self.name = name
    self.__opn_do_sw=pvname + ":OPN_SW"
    self.__opn_di=pvname + ":OPN_DI"
    self.__cls_di=pvname + ":CLS_DI"
    self.__opn_ok=pvname + ":OPN_OK"
                 

  def open(self):
    """ Opens a valve (sets OPN_DO_SW to High) """
    pypsepics.put(self.__opn_do_sw,1)
    
  def close(self):
    """ Closes a valve (sets OPN_DO_SW to Low) """
    pypsepics.put(self.__opn_do_sw,0)

  def isopen(self):
    """ return true if the valve is open """
    openswitch = pypsepics.get(self.__opn_di)
    if (openswitch ==1):
        return True
    else:
        return False

  def isclosed(self):
    """ return True if the valve is closed """
    closeswitch = pypsepics.get(self.__cls_di)
    if (closeswitch ==1):
        return True
    else:
        return False

  def openok(self):
    """  check wether valve is allowed to be open """
    return pypsepics.get(self.__opn_ok)

    
  def status(self):
    """ Returns the status of a valve """
    #openswitch = pypsepics.get(self.__opn_di)
    #closeswitch = pypsepics.get(self.__cls_di)
    if self.isopen():
      vstatus=estr("OPEN", color='green',type='normal')
    elif self.isclosed():
      vstatus=estr("CLOSED", color='red',type='normal')
    else:
      vstatus=estr("NOT KNOWN", color='red',type='normal')
    str1 ="%s:" % self.name 
    str2 =" %s" % vstatus 
    str = str1.rjust(9)+str2.ljust(13)
    return str

  def __repr__(self):
    return self.status()

class LeyboldValve:
  """ special Leybold Valve.
      These are not pneumatic, but electrical, usually small and on vent / purge lines.
      They don't have readback of their position, so whet commanded open, they are open,
      otherwise closed
  """
  def __init__(self,pvname,name):
    self.pvname=pvname
    self.name = name
    self.__opn_do_sw=pvname + ":OPN_SW"
    self.__opn_di=pvname + ":OPN_DO"
    self.__opn_ok=pvname + ":OPN_OK"
   
  def isclosed(self):
    """ returns True if valve is openclosed """
    openswitch = pypsepics.get(self.__opn_di)
    if (openswitch ==0):
        return True
    else:
        return False

  def open(self):
    """ Opens a valve (sets OPN_DO_SW to High) """
    pypsepics.put(self.__opn_do_sw,1)
    
  def close(self):
    """ Closes a valve (sets OPN_DO_SW to Low) """
    pypsepics.put(self.__opn_do_sw,0)

  def openok(self):
    """  check wether valve is allowed to be open """
    return pypsepics.get(self.__opn_ok)

  def isopen(self):
    """ return true if the valve is open """
    openswitch = pypsepics.get(self.__opn_di)
    if (openswitch ==1):
        return True
    else:
        return False

  def status(self):
    """ Returns the status of a valve """
    #openswitch = pypsepics.get(self.__opn_di)
    #closeswitch = pypsepics.get(self.__cls_di)
    if self.isopen():
      vstatus=estr("OPEN", color='green',type='normal')
    elif self.isclosed():
      vstatus=estr("CLOSED", color='red',type='normal')
    else:
      vstatus=estr("NOT KNOWN", color='red',type='normal')
    str1 ="%s:" % self.name 
    str2 =" %s" % vstatus 
    str = str1.rjust(9)+str2.ljust(13)
    return str

  def __repr__(self):
    return self.status()


  

class Gauge:
  """ 
  Gauge class : Used to control and monitor gauges
  Instances defined in xppbeamline.py
  """  
  def __init__(self,pvname,name):
    self.pvname=pvname
    self.name = name
    self.__pmon=pvname + ":PMON"
    self.__enbl_sw=pvname + ":ENBL_SW"
    self.__statusmon=pvname + ":STATUSMON"
    self.__pstatsprbck=pvname + ":PSTATSPRBCK"  # PLC trip point readback value
    self.__pstatspdes=pvname + ":PSTATSPDES"  # PLC trip point set value

#  def on(self):
#    """ Turns a CC gauge on """
#    pypsepics.put(self.__enbl_sw,1)
    
#  def off(self):
#    """ Turns a CC gauge off """
#    pypsepics.put(self.__enbl_sw,0)

  def trip(self,value=None):
    """ Sets or Returns the gauge trip point for the vacuum PLC """
    previous_trip=pypsepics.get(self.__pstatsprbck)
    if (value is not None):
      pypsepics.put(self.__pstatspdes,value)
      s = "Resetting PLC trip point of `%s` from %.4g to %.4g" % (self.name,previous_trip,value)
      logprint(s,print_screen=True)
    else:
      print "%s trip point is %.4g" % (self.name,previous_trip)

  def pressure(self):
    """ Returns the pressure """
    return pypsepics.get(self.__pmon)

  def status(self):
    """ Returns the gauge reading """
    g_on = pypsepics.get(self.__statusmon)
    if (g_on !=0):
      gstatus=estr("Gauge Off",color='white',type='normal')
      str="%s: %s" % (self.name,gstatus)
    else:
      pressure=pypsepics.get(self.__pmon)
      if pressure<5e-8:
        gstatus=estr("%.1e Torr" % pressure ,color='green',type='normal')
      elif pressure<1e-6:
        gstatus=estr("%.1e Torr" % pressure ,color='orange',type='normal')
      else:
        gstatus=estr("%.1e Torr" % pressure ,color='red',type='normal')
    str1 ="%s:" % self.name 
    str2 =" %s" % gstatus 
    str = str1.rjust(10)+str2.ljust(13)
    return str

  def __repr__(self):
    return self.status()

class IonPump:
  """ 
  IonPump class : Used to control and monitor IonPumps
  Instances defined in xppbeamline.py
  """  
  def __init__(self,pvname,name):
    self.pvname=pvname
    self.name = name
    self.__pmon=pvname + ":PMON" # Pressure in Torr
    self.__imon=pvname + ":IMON" # Current in Amps
    self.__vmon=pvname + ":VMON" # Voltage
    self.__statedes=pvname + ":STATEDES" # on/off control 
    self.__statemon=pvname + ":STATEMON" 
    self.__status=pvname + ":STATUS"
    self.__statuscode=pvname + ":STATUSCODE"
    self.__pumpsize=pvname + ":PUMPSIZE"
    self.__vpcname=pvname + ":VPCNAME" # controller running pumpHX3:MON:PIP:03:STATEDES

  def on(self):
    """ Turns a Ion Pump on """
    pypsepics.put(self.__statedes,1)
    
  def off(self):
    """ Turns a Ion Pump off """
    pypsepics.put(self.__statedes,0)
  
  def status(self):
    """ Returns the ion pump pressure reading """
    p_on = pypsepics.get(self.__statemon)
    if (p_on ==0):
      pstatus=estr("Ion Pump Off",color='white',type='normal')
    else:
      pressure=pypsepics.get(self.__pmon)
      if pressure<5e-8:
        pstatus=estr("%.2e Torr" % pressure ,color='green',type='normal')
      elif pressure<1e-6:
        pstatus=estr("%.2e Torr" % pressure ,color='orange',type='normal')
      else:
        pstatus=estr("%.2e Torr" % pressure ,color='red',type='normal')
    str1 ="%s:" % self.name 
    str2 =" %s" % pstatus 
    str = str1.rjust(8)+str2.ljust(16)
    return str

  def __repr__(self):
    return self.status()

  def info(self):
    """ Returns the ion pump information """
    current = pypsepics.get(self.__imon)
    voltage = pypsepics.get(self.__vmon)
    controller = pypsepics.get(self.__vpcname)
    pumpsize = pypsepics.get(self.__pumpsize)
    statemon = pypsepics.get(self.__statemon)
    if (statemon ==0):
      state=estr("Off",color='red',type='normal')
    elif (statemon ==1):
      state="On"
    else:
      state=estr("Unknown",color='white',type='normal')
    str="   %s\n" % (self.status())
    str += "   Current: %.2e Amps\n" % current
    str += "   Voltage: %4.0f Volts\n" % voltage
    str += "     State: %s\n" % state
    str += "      Size: %s l/s\n" % pumpsize
    str += "Controller: %s\n" % controller
    print str

class EbaraPump:
  """ class to control Ebara pumps """

  def __init__(self,pvname,name):
    self.pvname=pvname
    self.name = name
    self.__start=pvname + ":MPSTART_SW" # runstop button

  def run(self):
    """ starts the pump """
    pypsepics.put(self.__start,1)

  def stop(self):
    pypsepics.put(self.__start,0)

class TurboPump:
  """ class to control turbo pumps """

  def __init__(self,pvname,name):
    self.pvname=pvname
    self.name = name
    self.__start=pvname + ":START_SW" # runstop button

  def run(self):
    """ starts the pump """
    pypsepics.put(self.__start,1)

  def stop(self):
    pypsepics.put(self.__start,0)
  
  



