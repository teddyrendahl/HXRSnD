#from motor import Motor
from time import sleep,time
from pypslog import logprint
import pypsepics
import utilities
import motor_newport
import datetime
import pprint
import config
import simplejson
import shutil
from functools import partial

class VirtualMotor(object):
  def __init__(self,motorsobj,name,move,wm,wait=None,set=None,tolerance=None,direction=1,pvpos=None,pvoff=None,lowlim=None,hilim=None):
#    Motor.__init__(self,None,name,readbackpv=None,has_dial=False)
    self.name   = name
    self.__move_dial   = move
    self.__wm     = wm
    self.__wait   = wait
    self.tolerance = tolerance
    self.__set     = set
    self.pvname = "virtual motor"
    self.pvpos = pvpos; # position pv
    self.pvoff = pvoff; # offset pv
    self.direction = direction/abs(direction)
    self.low_dial_lim = lowlim
    self.high_dial_lim = hilim
    self.move_silent = self.move
    self.__desidered_value = None
    motorsobj.__setattr__(self.name,self)

  def set(self,value):
    if (self.__set is not None):
      self.__set(value)
    elif (self.pvoff is not None):
      offset = value - self.direction*self.wm_dial()
      pypsepics.put(self.pvoff,offset)
      sleep(0.1); # gives epics time to update offset pv
      self.wm()
    else:
      print "user position not defined for this motor"
      
  def wm(self):
    if (self.pvoff is None):
      offset=0
    else:
      offset=pypsepics.get(self.pvoff)
    user = self.direction*self.wm_dial()+offset
    if (self.pvpos is not None):
      pypsepics.put(self.pvpos,user)
    return user

  def move(self,value):
    if (self.pvoff is None):
      offset=0
    else:
      offset=pypsepics.get(self.pvoff)
    dial = (value-offset)*self.direction
    self.move_dial(dial)
    return value

  def wm_string(self):
    return self.wm()

  def wm_dial(self):
    pos = self.__wm()
    return pos

  def move_dial(self,value):
    if (self.low_dial_lim is not None):
      check_low = (value>=self.low_dial_lim)
    else:
      check_low = True
    if (self.high_dial_lim is not None):
      check_high = (value<=self.high_dial_lim)
    else:
      check_high = True
    check = check_low and check_high
    if (not check):
      logprint("Asked to move %s (pv %s) to dial %f that is outside limits, aborting" % (self.name,self.pvname,value),print_screen=1)
    else:
      self.__desidered_value = value
      self.__move_dial(value)
      pos=self.wm()

  def __is_motor_moving(self):
    initial_pos = self.wm()
    sleep(0.1)
    check = (self.wm_dial()==initial_pos)
    if (check):
      self.__desidered_value = initial_pos
    return (not check)
    
  def wait(self):
    if (self.__wait is not None):
      self.__wait()
    elif (self.tolerance is None):
      while( self.__is_motor_moving() ):
        pass
    else:
      initial_pos = self.wm()
      if (self.__desidered_value is None):
        while( self.__is_motor_moving() ):
          pass
      else:
        t0 = time()
        while (abs(self.wm()-self.__desidered_value)>self.tolerance):
          sleep(0.01)
          if ( ((time()-t0)>0.1) and  (not self.__is_motor_moving) ):
            break
    pos = self.wm()
     
  def update_move_relative(self,howmuch,show_previous=True):
    pos = self.wm()
    self.update_move(pos+howmuch,show_previous)
    
  def umvr(self,howmuch,show_previous=True): self.update_move_relative(howmuch,show_previous)
              
  def update_move_dial(self,value,show_previous=True):
    if (show_previous):
      print "initial position: %s" % self.wm_dial()
    self.move_dial(value)
    sleep(0.1)
    while ( self.__is_motor_moving() ):
      s = "motor position: %s" % self.wm_dial()
      utilities.notice(s)
      sleep(0.05)
    s = "motor position: %s" % self.wm_dial()
    utilities.notice(s)
    print ""

  def update_move(self,value,show_previous=True):
    if (show_previous):
      print "initial position: %s" % self.wm_string()
    self.move(value)
    sleep(0.1)
    while ( self.__is_motor_moving() ):
      s = "motor position: %s" % self.wm_string()
      utilities.notice(s)
      sleep(0.05)
    s = "motor position: %s" % self.wm_string()
    utilities.notice(s)
    print ""


#    deadband = self.get_par("retry_deadband")
#    usergoto = self.wm_desired_user()
#    delta=abs(usergoto-initial_pos)
#    if (  delta<deadband ): return
#    sleep(0.02)
#    t0=time()
#    while ( not self.__isthere() ):
#      sleep(0.01)
#      if ( ( (time()-t0) > 0.1 ) & (self.wm()==initial_pos) ):
#        # if in 100ms motor position is the same ... we must not be moving
#        self.__user_desidered_pos = self.get_par("drive");
#        break



  def __call__(self,value):
    self.move(value)

  def __repr__(self):
    return self.status()

  def status(self):
    s  = "virtual motor %s\n" % self.name
    s += "  current position (user,dial): (%.4g,%.4g)\n" % (self.wm(),self.wm_dial())
    if (self.direction>0):
      dir = "not inverted"
    else:
      dir = "inverted"
    s += "  user vs dial direction: %s\n" % dir
    if (self.low_dial_lim is None):
      lowlim="None"
    else:
      lowlim="%.4g" % self.low_dial_lim
    if (self.high_dial_lim is None):
      highlim="None"
    else:
      highlim="%.4g" % self.high_dial_lim
    s += "  dial limits (low,high): (%s,%s)\n" % (lowlim,highlim)
    return s

  def move_relative(self,howmuch):
    p = self.wm()
    if (howmuch == 0):
      return p
    else:
      return self.move(p+howmuch)

  def mvr(self,howmuch): self.move_relative(howmuch)

  def  mv(self,value):   self.move(value)

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
    if raw_input('Do you really like to delete all presets of this motors?') is 'y':
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
