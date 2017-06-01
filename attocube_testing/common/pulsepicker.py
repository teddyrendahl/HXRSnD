import pypslog
import pyca
class PulsePicker:
  """beamrate only needed for automatic delay for pulsing"""

  def __init__(self,evr,lcls,trigger=0,out=0,polarity="Normal",ystage=None):
    self.__trigger=trigger
    self.__out = out
    self.lcls  = lcls
    self.pos = ystage
    if (polarity=="Normal"):
      self.__polarity = 0
    else:
      self.__polarity = 1

    self.lcls= lcls
    # default event number to use (note this is not the event code but just the
    # position in the list of events
    self.__event_number = 13;
    self.evr = evr
  
  def status(self):
    self.evr.polarity()

  def reset(self):
    self.evr.setDefaults()

  def open(self,fast=False):
    """ open the shutter; the option fast when enable skip the test
    that makes sure that the output is not triggered by any event code"""
    if (not fast):
      self.evr.disableAllEvents()
    self.evr.polarity(self.__polarity);
    
  def close(self,fast=False):
    """ close the shutter; the option fast when enable skip the test
    that makes sure that the output is not triggered by any event code"""
    if (not fast):
      self.evr.disableAllEvents()
    self.evr.polarity(not self.__polarity)

  def prepare_for_pulse(self,delay="auto",opening_time=14e-3,event_code=84,npulses=1):
    """ Prepare the pulse picker for pulsed operation; default event code is
    84 """
    # assign trigger to out
    if ( (self.lcls is None) and (delay=="auto") ):
      print "PulsePicker.prepare_for_pulse: Asked for automatic delay but need to know the lcls_beamrate"
      return
    self.close()
    beamrate=self.lcls.get_xraybeamrate()
    self.evr.enable(); # enable trigger
    self.evr.prescale(119)
    if (delay == "auto"):
      trigger_to_open = 5.0e-3; # assumed not measured
      evr_to_beam     = 0.9e-3
      delay = evr_to_beam + 1./beamrate - (trigger_to_open+opening_time/2.)
      print "Delay: %f" % delay
      if (delay<0):
        print "The automatic delay calculation returned a negative number ... this means that the machine is running at too high frequency for the shutter to work in a simple way (measuring on the next pulse). Ask to lower the rep rate"
        return
    else:
      delay = float(delay)
    self.evr.delay(trigger)
    opening_time = opening_time + (npulses-1)/beamrate
    print "Opening time: %f" % opening_time
    self.evr.width(opening_time)
    self.evr.fireOnEventCode(event_code)

#pp = PulsePicker(m.pp_y,trigger=0,out=0,polarity="Inverted")
#lp = PulsePicker(None,trigger=1,out=1,polarity="Inverted")

