import numpy
import pypsepics
import utilities
import sys,os,shutil
from pypslog import logprint
from time import sleep,time
from utilitiesMotors import estimatedTimeNeededForMotion,tweak
import config
import datetime
import pprint,new
import simplejson
from functools import partial
from pswww import pypsElog

motor_params = {
   'acceleration':    ('ACCL', 'acceleration time'),
   'back_accel':      ('BACC', 'backlash acceleration time'),
   'backlash':        ('BDST', 'backlash distance'),
   'back_speed':      ('BVEL', 'backlash speed'),
   'card':            ('CARD', 'Card Number '),
   'dial_high_limit': ('DHLM', 'Dial High Limit '),
   'direction':       ('DIR',  'User Direction '),
   'dial_low_limit':  ('DLLM', 'Dial Low Limit '),
   'settle_time':     ('DLY',  'Readback settle time (s) '),
   'done_moving':     ('DMOV', 'Done moving to value'),
   'dial_readback':   ('DRBV', 'Dial Readback Value'),
   'description':     ('DESC', 'Description'),
   'dial_drive':      ('DVAL', 'Dial Desired Value'),
   'units':           ('EGU',  'Engineering Units '),
   'encoder_step':    ('ERES', 'Encoder Step Size '),
   'freeze_offset':   ('FOFF', 'Offset-Freeze Switch '),
   'move_fraction':   ('FRAC', 'Move Fraction'),
   'hi_severity':     ('HHSV', 'Hihi Severity '),
   'hi_alarm':        ('HIGH', 'High Alarm Limit '),
   'hihi_alarm':      ('HIHI', 'Hihi Alarm Limit '),
   'high_limit':      ('HLM',  'User High Limit  '),
   'high_limit_set':  ('HLS',  'High Limit Switch  '),
   'hw_limit':        ('HLSV', 'HW Lim. Violation Svr '),
   'home_forward':    ('HOMF', 'Home Forward  '),
   'home_reverse':    ('HOMR', 'Home Reverse  '),
   'high_op_range':   ('HOPR', 'High Operating Range'),
   'high_severity':   ('HSV',  'High Severity '),
   'integral_gain':   ('ICOF', 'Integral Gain '),
   'jog_accel':       ('JAR',  'Jog Acceleration (EGU/s^2) '),
   'jog_forward':     ('JOGF', 'Jog motor Forward '),
   'jog_reverse':     ('JOGR', 'Jog motor Reverse'),
   'jog_speed':       ('JVEL', 'Jog Velocity '),
   'last_dial_val':   ('LDVL', 'Last Dial Des Val '),
   'low_limit':       ('LLM',  'User Low Limit  '),
   'low_limit_set':   ('LLS',  'At Low Limit Switch'),
   'lo_severity':     ('LLSV', 'Lolo Severity  '),
   'lolo_alarm':      ('LOLO', 'Lolo Alarm Limit  '),
   'low_op_range':    ('LOPR', 'Low Operating Range '),
   'low_alarm':       ('LOW', ' Low Alarm Limit '),
   'last_rel_val':    ('LRLV', 'Last Rel Value  '),
   'last_dial_drive': ('LRVL', 'Last Raw Des Val  '),
   'last_SPMG':       ('LSPG', 'Last SPMG  '),
   'low_severity':    ('LSV',  'Low Severity  '),
   'last_drive':      ('LVAL', 'Last User Des Val'),
   'soft_limit':      ('LVIO', 'Limit violation  '),
   'in_progress':     ('MIP',  'Motion In Progress '),
   'missed':          ('MISS', 'Ran out of retries '),
   'moving':          ('MOVN', 'Motor is moving  '),
   'resolution':      ('MRES', 'Motor Step Size (EGU)'),
   'motor_status':    ('MSTA', 'Motor Status  '),
   'offset':          ('OFF',  'User Offset (EGU) '),
   'output_mode':     ('OMSL', 'Output Mode Select  '),
   'output':          ('OUT',  'Output Specification '),
   'prop_gain':       ('PCOF', 'Proportional Gain '),
   'precision':       ('PREC', 'Display Precision '),
   'readback':        ('RBV',  'User Readback Value '),
   'retry_max':       ('RTRY', 'Max retry count    '),
   'retry_count':     ('RCNT', 'Retry count  '),
   'retry_deadband':  ('RDBD', 'Retry Deadband (EGU)'),
   'dial_difference': ('RDIF', 'Difference rval-rrbv '),
   'raw_encoder_pos': ('REP',  'Raw Encoder Position '),
   'raw_high_limit':  ('RHLS', 'Raw High Limit Switch'),
   'raw_low_limit':   ('RLLS', 'Raw Low Limit Switch'),
   'relative_value':  ('RLV',  'Relative Value    '),
   'raw_motor_pos':   ('RMP',  'Raw Motor Position '),
   'raw_readback':    ('RRBV', 'Raw Readback Value '),
   'readback_res':    ('RRES', 'Readback Step Size (EGU)'),
   'raw_drive':       ('RVAL', 'Raw Desired Value  '),
   'dial_speed':      ('RVEL', 'Raw Velocity '),
   's_speed':         ('S',    'Speed (RPS)  '),
   's_back_speed':    ('SBAK', 'Backlash Speed (RPS)  '),
   's_base_speed':    ('SBAS', 'Base Speed (RPS)'),
   's_max_speed':     ('SMAX', 'Max Velocity (RPS)'),
   'set':             ('SET',  'Set/Use Switch '),
   'stop_go':         ('SPMG', 'Stop/Pause/Move/Go '),
   's_revolutions':   ('SREV', 'Steps per Revolution '),
   'stop':            ('STOP', 'Stop  '),
   't_direction':     ('TDIR', 'Direction of Travel '),
   'tweak_forward':   ('TWF',  'Tweak motor Forward '),
   'tweak_reverse':   ('TWR',  'Tweak motor Reverse '),
   'tweak_val':       ('TWV',  'Tweak Step Size (EGU) '),
   'use_encoder':     ('UEIP', 'Use Encoder If Present'),
   'u_revolutions':   ('UREV', 'EGU per Revolution  '),
   'use_rdbl':        ('URIP', 'Use RDBL Link If Present'),
   'drive':           ('VAL',  'User Desired Value'),
   'base_speed':      ('VBAS', 'Base Velocity (EGU/s)'),
   'slew_speed':      ('VELO', 'Velocity (EGU/s) '),
   'version':         ('VERS', 'Code Version '),
   'max_speed':       ('VMAX', 'Max Velocity (EGU/s)'),
   'use_home':        ('ATHM', 'uses the Home switch'),
   'deriv_gain':      ('DCOF', 'Derivative Gain '),
   'use_torque':      ('CNEN', 'Enable torque control '),
   'device_type':     ('DTYP', 'Device Type'),
   'record_type':     ('RTYP', 'Record Type'),
   'status':          ('STAT', 'Status')
}

class Motor(object):
  """ 
  motor module
  define a new motor as 
  mymot = motor("XPP:SB2:MMS:10",name="mymotname")
 
  Usage example:

  -> ASK POSITION  <-
  mymot.wm();        # returns current user position
  mymot.wm_string(); # returns current user position as string
  mymot.wm_dial();   # returns current dial position
  mymot.wm_raw();    # returns current motor number of steps

  -> MOVE ABSOLUTE (user value) <-
  mymot.move(3);
  mymot.mv(3);           # as above
  mymot.move_silent(3);  # don't write anything to terminal, good for macros
  mymot.update_move(3);  # show changing postion
  mymot.umv(3);          # show changing postion

  -> MOVE RELATIVE (user value) <-
  mymot.move_relative(2);
  mymot.mvr(2);                  # as above
  mymot.update_move_relative(2); # show changing position
  mymot.umvr(2)                  # show changing position

  -> ASK/CHANGE STATUS <-
  mymot.set(4)          # call current position 4 in user coordinates
  mymot.set_dial(4)     # call current dial position 4 leaving the .OFF unaltered
  mymot.ismoving();     # True if moving
  mymot.stop();         # Send a stop command
  mymot.[get/set]_speed # to change or retrieve current speed (in EGU/s)
    
  """
  def __init__(self,pvname,name=None,readbackpv="default",home="low",presets = dict(),sioc_pv=None):
    self.__name__   = "xpp motor class"
    self._sioc_pv=sioc_pv #pv name of the soft ioc. used to reset ioc after reconnection/failure
    self.pvname     = pvname
    if (name is None): name = self.get_par("description")
    self.name       = name
    if (home is None): home = ""
    self.__home = home
    if (readbackpv is None):
      self.readback   = pvname
    elif (readbackpv == "default"):
      self.__readbackpv   = pvname + ".RBV"
    else:
      self.__readbackpv   = readbackpv
    self.__dialpv       = pvname + ".DVAL"
    # keep local copy of .VAL to avoid slow IOC not updating fast enough
    self.__user_desidered_pos = None

  def home(self,ask=True,move_motor_back=True):
    #rewritten from Marco original.
    if (self.__home != ("low" or "high")):
      print "no home position defined for motor %s (pv %s), returning" % (self.name,self.pvname)
      return
    if (self.get_par('direction')==0):
      dir=1
    else:
      dir=-1
    orig_user_pos = self.wm()
    orig_speed    = self.get_speed()
    dial_offset = 100; # in EGU
    move_away   = 5000; # in motor steps
    resolution = self.get_par("resolution")
    if (self.__home == "low"):
      oldlow=self.get_lowlim()
      target = oldlow
      self.set_lowlim(oldlow-10)
      sign=-1
    elif (self.__home == "high"):
      oldhilim=self.get_hilim()
      target = oldhilim
      self.set_hilim(oldhilim+10)
      sign=1
    else:
      print "inconsistent state in home, aborting"
      return
    try:
      self.move(target)
      print("howe to "+self.__home+" limit switch ...")
      lim = self.wait_for_switch()
      lim_pos = self.wm()
      if (lim != self.__home):
          print "Asked for %s limit switch, got %s, aborting" % (self.__home,lim)
          return
      print "Reached %s limit switch, current user pos %f" % (self.__home,lim_pos)
      self.move(lim_pos-sign*move_away*resolution); # move a bit away from limit
      self.wait()
      self.set_speed(self.get_par("base_speed")); # use base speed as low speed option
      self.move(lim_pos+sign*2*move_away*resolution); # move back to limit switch
      lim = self.wait_for_switch()
      dial_at_lim = self.wm_dial()
      print dial_at_lim
      print "Reached %s limit switch, current dial %f" % (self.__home,dial_at_lim)
      if (ask):
        repl = raw_input("Motor %s (pv %s) is now at %s limit switch, want to set the dial to zero ? [y/n]\n" % (self.name,self.pvname,self.__home))
        if (repl.lower()[0] == "y"):
          self.set_dial(0)   
        else:
          print "exiting living the motor at limit switch "
          #set_dial_f(0) # same as below
          return
      #set_dial_f(0)  # uncomment if you want the softlimit to be the same as limit switch
      print "homing procedure for motor %s (pv %s) finished" % (self.name,self.pvname)
    finally:
      self.set_speed(orig_speed)
      if (move_motor_back):
        self.move(orig_user_pos-dir*dial_at_lim)
        print "moving motor back to original position (%f)" % self.wm()


  def reset(self):
    if self._sioc_pv==None: print "no SIOC pvname defined. Cannot reset."
    else: pypsepics.put(self._sioc_pv+":SYSRESET",1)
    
        
   
  def wait_for_switch(self):
    lim = self.check_limit_switches()[0]
    while (self.check_limit_switches()[0] == "ok"):
      utilities.notice("waiting for limit seitch of motor %s (pv %s)" % (self.name,self.pvname))
      sleep(0.2)
    return self.check_limit_switches()[0]
    

  def __call__(self,value=None):
    """ Shortcut for move, for example: m.gonx(4)
        if no value is passed, it is a shortcut for .wm()"""
    if value==None: return self.wm()
    else: self.move(value)

  def __repr__(self):
    return self.status()

  def status(self):
    """ return info for the current motor"""
    str  = "%s\n\tpv %s\n" % (self.name,self.pvname)
    str += "\tcurrent position (user,dial): %f,%f\n" % (self.wm(),self.wm_dial())
    str += "\tuser limits      (low,high) : %f,%f" % (self.get_lowlim(),self.get_hilim())
    return str

#  def __repr__(self):
#    """ return info for the current motor, useful to use as: m.gonx (+Enter)"""
#    return self.status()

  def __str__(self):
    """ short string representation of motor """
    return "%s @ user %s" % (self.name,self.wm_string())

  # functions for user position
  def wm_desired_user(self):
    if self.__user_desidered_pos is None:
      self.__user_desidered_pos = self.get_par("drive");
    return self.__user_desidered_pos

  def wm(self):
    """ returns readback position as float number"""
    return pypsepics.get(self.__readbackpv)
  def wm_offset(self):
    """ returns .OFF PV"""
    return self.get_par("offset")

  def wm_string(self):
    """ returns readback position as string with the right number of decimals"""
    prec = int(self.get_par("precision"))
    format = "%%0.%df" % prec
    return format % self.wm()

  def move_silent(self,value):
    return self.move(value)

  def move(self,value):
    self.__user_desidered_pos = value
    if ( (value<self.get_lowlim()) or (value>self.get_hilim()) ):
      logprint("Asked to move %s (pv %s) to %f, limits are %f-%f, aborting" % (self.name,self.pvname,value,self.get_lowlim(),self.get_hilim()),print_screen=1)
      return self.wm()
    (status,msg) = self.check_limit_switches()
    if ( (status == "high") and (value>self.wm() ) ):
      logprint(msg+",aborting",print_screen=1)
      return self.wm()
    elif ( (status == "low") and (value<self.wm() ) ):
      logprint(msg+",aborting",print_screen=1)
      return self.wm()
    logprint("moving %s (pv %s) to %f, previous position: %f" % (self.name,self.pvname,value,self.wm()))
    #return pypsepics.put(self.pvname,value)
    return self.put_par("drive",value)
    
  def check_limit_switches(self):
    if self.get_par("low_limit_set"):
      return ("low","low limit switch for motor %s (pv %s) activated" % (self.name,self.pvname))
    elif (self.get_par("high_limit_set")):
      return ("high","high limit switch for motor %s (pv %s) activated" % (self.name,self.pvname))
    else:
      return ("ok","")

  def estimatedTimeForMotion(self,deltaS):
    vBase = self.get_par("base_speed")
    vFull = self.get_par("slew_speed")
    Acc = (vFull-vBase)/self.get_par("acceleration")
    if Acc==0: Acc=1 #This is an ugly hack, to stop a division by 0 which I get with with tgx
    return estimatedTimeNeededForMotion(deltaS,vBase,vFull,Acc)


#  user = property(wm,move)
  def mv(self,value): self.move(value)

  def update_move(self,value,show_previous=True):
    """ move motor to value while displaying motor position
        Crtl + C stops motor """
    if (show_previous):
      print "initial position: %s" % self.wm_string()
    tn = self.estimatedTimeForMotion(value-self.wm())
    t0 = time()
    self.move(value)
    sleep(0.02)
    try:
      while ( not self.__isthere() ):
        s = "motor position: %s" % self.wm_string()
        utilities.notice(s)
        sleep(0.01)
    except KeyboardInterrupt:
      print "Ctrl + C pressed. Stopping motor"
      self.stop()
      sleep(1)
    s = "motor position: %s" % self.wm_string()
    utilities.notice(s)
    print "Time needed %.3f (estimated time %.3f)" % (time()-t0,tn)

  def umv(self,value): self.update_move(value)



  def mv_elog(self,value,ElogQuestion=True):
    oldpos = self.wm()
    print "...moving %s to %g" %(self.name,value)
    self.umv(value)
    if ElogQuestion:
      if raw_input('Would you like to send this move to the logbook? (y/n)\n') is 'y':
        elogStr = "Moved %s from %g by %g to %g." %(self.name,oldpos,value-oldpos,value)
        pypsElog.submit(elogStr)

  def mvr_elog(self,value,ElogQuestion=True):
    oldpos = self.wm()
    print "...moving %s to %g" %(self.name,value)
    self.umvr(value)
    newpos = self.wm()
    if ElogQuestion:
      if raw_input('Would you like to send this move to the logbook? (y/n)\n') is 'y':
        elogStr = "Moved %s from %g by %g to %g." %(self.name,oldpos,value,newpos)
        pypsElog.submit(elogStr)



  # limits functions
  def set_lims(self,*args):
    if len(args)==1:
      print "please input two values for lower and higher limit"
    elif len(args)==2:
      mnval = np.min(args)
      mxval = np.max(args)
      self.put_par("low_limit",mnval)
      self.put_par("high_limit",mxval)
    else:
      print 'Limits input not understood --> no change of limits'

  def set_lims_relative(self,*args):
    ppos = self.wm()
    if len(args)==1:
      relval = np.abs(args[0])
      self.put_par("low_limit",ppos-relval)
      self.put_par("high_limit",ppos+relval)
    elif len(args)==2:
      mnval = np.min(args)
      mxval = np.max(args)
      self.put_par("low_limit",ppos-mnval)
      self.put_par("high_limit",ppos+mxval)
    else:
      print 'Limits imput not understood --> no change of limits'

  def get_lims(self):
    return [self.get_par("low_limit"),self.get_par("high_limit")]

  
  def get_hilim(self):
    return self.get_par("high_limit")
  def set_hilim(self,value):
    self.put_par("high_limit",value)
  def get_lowlim(self):
    return self.get_par("low_limit")
  def set_lowlim(self,value):
    self.put_par("low_limit",value)
  def get_dial_hilim(self):
    return self.get_par("dial_high_limit")
  def set_dial_hilim(self,value):
    self.put_par("dial_high_limit",value)
  def get_dial_lowlim(self):
    return self.get_par("dial_low_limit")
  def set_dial_lowlim(self,value):
    self.put_par("dial_low_limit",value)

  # functions for dial position
  def wm_desired_dial(self):
    return self.get_par("dial_drive")
  def wm_dial(self):
    return self.get_par("dial_readback")

  def move_dial(self,value):
    try:
      if ( (value<self.get_dial_lowlim()) or (value>self.get_dial_hilim()) ):
        logprint("Asked to move %s (pv %s) outside limit, aborting" % (self.name,self.pvname),print_screen=1)
        return self.wm_dial()
      (status,msg) = self.check_limit_switches()
      if ( (status == "high") and (value>self.wm_dial() ) ):
        logprint(msg,print_screen=1)
        return self.wm_dial()
      elif ( (status == "low") and (value<self.wm_dial() ) ):
        logprint(msg,print_screen=1)
        return self.wm_dial()
    except:
      pass
    return pypsepics.put(self.__dialpv,value)
#  dial = property(wmdial,move_dial)

  # functions for raw position
  def wm_raw(self):
    return self.get_par("raw_drive")
  def move_raw(self,value):
    return self.put_par("raw_drive",value)
#  raw = property(get_raw,set_raw)

  # functions for speed
  def get_speed(self):
    """ return the speed (.VELO) in EGU/s """
    return self.get_par("slew_speed")

  def set_speed(self,value):
    """ set the speed (.VELO) in EGU/s """
    if (value>self.get_par("max_speed")):
      print "asked to set the speed to %f but the max speed is %f\n" % (value,self.get_par("max_speed"))
      print "use caput %s.VMAX %f to increase max speed\n" % (self.pvname,value)
    else:
      return self.put_par("slew_speed",value)
#  speed = property(get_speed,set_speed)

  def move_relative(self,howmuch):
    if (howmuch == 0): return self.wm()
    current = self.wm()
    if (numpy.isnan(current)):
      logprint("Problem retriving current position for motor %s (pv %s)... not continuing" % self.name,self.pvname)
      return None
    else:
      return self.move(current+howmuch)

  def mvr(self,howmuch): self.move_relative(howmuch)

  def update_move_relative(self,howmuch,show_previous=True):
    pos = self.wm()
    self.update_move(pos+howmuch,show_previous)

  def umvr(self,howmuch,show_previous=True): self.update_move_relative(howmuch,show_previous)

  def stop(self):
    self.put_par("stop",1)

  def ismoving(self):
    return (not pypsepics.get(self.pvname + ".DMOV"))

  def __isthere(self):
    deadband = self.get_par("retry_deadband")
    usergoto = self.wm_desired_user()
    delta=abs(usergoto-self.wm())
    return  ( delta<10*deadband and not self.ismoving() )

  def wait(self):
    deadband = self.get_par("retry_deadband")
    usergoto = self.wm_desired_user()
    initial_pos = self.wm()
    delta=abs(usergoto-initial_pos)
    if (  delta<deadband ): return
    sleep(0.02)
    t0=time()
    while ( not self.__isthere() ):
      sleep(0.01)
      if ( ( (time()-t0) > 0.1 ) ):
        # if in 100ms motor position is the same ... we must not be moving
        self.__user_desidered_pos = self.get_par("drive");
        # update internal desidered pos after 100ms
        # (because another session might have changed the target position
#        self.__user_desidered_pos = self.get_par("drive");
        

  def tweak(self,step=0.1,dir=1):
    tweak(self,step=step,dir=dir)
 


  def __sign(self):
    dir = self.get_par("direction"); # 1 means inverted
    if (dir == 1):
      return -1
    elif (dir == 0):
      return 1
    else:
      return None

  def set_dial(self,value=0,show_previous=True):
    previous_dial = self.wm_dial()
    previous_user = self.wm()
    self.put_par("set",1); # go in set mode
    sleep(0.1); # to make sure we are in set mode
    if (self.get_par("set") != 1):
      print "Failed to go in set mode, try again"
      return
    self.put_par("dial_drive",value)
    self.put_par("set",0); # go in use mode
    current_user = self.wm()
    s = "Resetting dial `%s` (PV: %s) from (dial,user) = (%.4g,%.4g) to (%.4g,%.4g)" % (self.name,self.pvname,previous_dial,previous_user,value,current_user)
    logprint(s,print_screen=True)


  def set(self,value=0,show_previous=True):
    # EPICS does user = dial + offset
    # offset = value + self.__sign()*self.wm_dial()
    current_dial = self.wm_dial()
    current_user = self.wm()
    offset = value - self.__sign()*current_dial
    if (show_previous):
      s = "Resetting user `%s` (PV: %s) from (dial,user) = (%.4g,%.4g) to (%.4g,%.4g)" % (self.name,self.pvname,current_dial,current_user,current_dial,value)
      logprint(s,print_screen=True)
      self.put_par("offset",offset)
      
  def get_pvname(self,parname):
    return self.pvname + "." + motor_params[parname][0]

  def get_par(self,parname):
    pv = self.get_pvname(parname)
    return pypsepics.get(pv)

  def put_par(self,parname,value):
    pv = self.get_pvname(parname)
    return pypsepics.put(pv,value)

  def expert_screen(self):
    """ Opens Epics motor expert screen for resetting motor after e.g. stalling"""
    os.system('~/bin/launch-motor.sh '+self.pvname)

  def archive(self,time_int=30,plotit=True):
    """Extracts epics archive data of motor readback and dial_readback time_int days back (default is 30). time_int can also be passed a datestring (startdate from which to plot), or a list of timestrings (time interval to plot)."""	  
    pospv = self.get_pvname('readback')
    dialpv = self.get_pvname('dial_readback')
    [tpos,xpos] = config.epicsarchive_xpp.pv_archive_data(pospv,time_int)
    [tdia,xdia] = config.epicsarchive_xpp.pv_archive_data(dialpv,time_int)
    if plotit:
      import pylab as pl
      import tools as tl
      figname = "%s (%s) archive" %(self.name,self.pvname)
      tl.nfigure(figname)

      sph1 = pl.subplot(211)
      pl.ylabel(pospv)
      pl.plot(tpos,xpos,'.-k')
      sph2 = pl.subplot(212,sharex=sph1)
      pl.ylabel(dialpv)
      pl.plot_date(tdia,xdia,'.-k')
    else:
      return [tpos,xpos,tpos,xdia]

  def _presets(self):
    if config.motor_presets:	  
      motor_presets = config.motor_presets
      if self.name in  motor_presets:
        return motor_presets[self.name]
  def _set_preset(self,name='',descr='',pos=[]):
    dt = datetime.datetime.now()	  
    config.motor_presets = self._rdpresets()
    if not pos:
      pos = self.wm()
    if not name:
      name = 'preset_'+dt.strftime('%Y%h%d-%Hh%Mm')
    if not config.motor_presets:
      config.motor_presets=dict()
    if self.name not in config.motor_presets:      
      config.motor_presets[self.name]=dict()      
    if name not in config.motor_presets[self.name]:      
      config.motor_presets[self.name][name]=dict()      
    config.motor_presets[self.name][name]['pos']=pos      
    config.motor_presets[self.name][name]['descr']=descr
    config.motor_presets[self.name][name]['time_set']=dt.isoformat()
    self._write_all_presets()
    self._init_presets()

  def _rdpresets(self):
    presetfile = config._motor_preset_path+'motor_presets'	  
    try:	  
      f = open(presetfile)
      pres = eval(f.read())
      f.close()
      return pres
    except:
      print "Motor presets file not found (%s)." %presetfile	    
      return dict()

  def _clear_preset(self,name=''):
    if not config.motor_presets:
      config.motor_presets=dict()
    if self.name not in config.motor_presets:      
      config.motor_presets[self.name]=dict()      
    if name in config.motor_presets[self.name]:      
      del config.motor_presets[self.name][name]
      del self.__dict__['mv_'+name]
      del self.__dict__['wm_'+name]
    else:
      print "The preset %s requested for deletion was not found!"	    
    self._write_all_presets()
  def _clear_all_presets(self):
    if raw_input('Do you really like to delete all presetsof this motors?') is 'y':
      for tp in config.motor_presets[self.name].keys():
        self._clear_preset(tp)
  def _write_all_presets(self):
    self.__clean_presets()
    presetpath = config._motor_preset_path
    datnow = datetime.datetime.now()
    preset_file = presetpath+'motor_presets_'+datnow.strftime('%Y-%m-%d_%H:%M:%S')
    f=open(preset_file,'w')
    f.write(simplejson.dumps(config.motor_presets,sort_keys=True,indent=3))
    f.close()
    preset_file = presetpath+'motor_presets'
    f=open(preset_file,'w')
    f.write(simplejson.dumps(config.motor_presets,sort_keys=True,indent=3))
    f.close()
    #shutil.copy2(preset_file,presetpath+'motor_presets')

  def _mv_preset(self,pos=[],name=''):
    if not pos: pos=0	  
    self.mv(pos+config.motor_presets[self.name][name]['pos'])
  def _umv_preset(self,pos=[],name=''):
    if not pos: pos=0	  
    self.umv(pos+config.motor_presets[self.name][name]['pos'])
  def _wm_preset(self,name=''):
    preset_pos = self.wm()
    preset_pos=preset_pos-config.motor_presets[self.name][name]['pos']
    return preset_pos
  def _init_presets(self):
    if self.name in config.motor_presets.keys():
      for preset in config.motor_presets[self.name].keys():
        if config.motor_presets[self.name][preset]:	
          self.__dict__['wm_'+preset] =  partial(self._wm_preset,name=preset)
          self.__dict__['mv_'+preset] = partial(self._mv_preset,name=preset)
          self.__dict__['umv_'+preset] = partial(self._umv_preset,name=preset)
  def __clean_presets(self):
    mots=config.motor_presets.keys();
    for mot in mots:
      if not config.motor_presets[mot]:	    
        del config.motor_presets[mot]   
    	  
