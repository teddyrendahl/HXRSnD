""" Generic functions that can act on multiple motors """

import pypsepics
from utilities import estr
import KeyPress
import time
import pyca
import sys
import motor as mmm
import virtualmotor as vvv
import numpy as np

def select_MMS_motors(motor_obj,string=None):
  """ returns a list of PV names found in the motors object (for example xppmotors)
      Optionally a string can be used to select only those PVnames that contain that string """
  nlist = motor_obj.__dict__.keys()
  mlist = []
  for i in nlist:
    m = motor_obj.__getattribute__(i)
    try:
      if (m.pvname.find("MMS") > 0):
        if (string is None):
          mlist.append(m.pvname)
        elif (m.pvname.find(string)>0):
          mlist.append(m.pvname)
        else:
          pass
    except:
      pass
  mlist.sort()
  return mlist

def select_CLZ_motors(motor_obj,string=None):
  """ returns a list of PV names found in the motors object (for example xppmotors)
      Optionally a string can be used to select only those PVnames that contain that string """
  nlist = motor_obj.__dict__.keys()
  mlist = []
  for i in nlist:
    m = motor_obj.__getattribute__(i)
    try:
      if (m.pvname.find("CLZ") > 0):
        if (string is None):
          mlist.append(m.pvname)
        elif (m.pvname.find(string)>0):
          mlist.append(m.pvname)
        else:
          pass
    except:
      pass
  mlist.sort()
  return mlist


def save_motors_pos(motor_list,outfile=None):
  """ display (and optionally save if outfilename is given) the motor positions for
      a list of motors (not PVs!) """
  if (not isinstance(motor_list,list)):
    motor_list = [motor_list]
  for m in motor_list:
    print m.name,m.wm()
  if (outfile is not None):
    f=open(outfile,"w")
    for m in motor_list:
      f.write("%s %e\n" % (m.name,m.wm()))
    f.close()
    

def load_motors_pos(motorsobj,infile):
  """ load and move motors, motor names and positions are taken from file, motors
      are found in motorsobj (for example xppmotors) """
  f=open(infile,"r")
  lines = f.readlines()
  f.close()
  for l in lines:
    (mname,pos) = l.split(); pos=float(pos)
    print mname,pos
    m = find_motor_by_name(motorsobj,mname)
    if (m is not None):
      print "moving %s to %e (previous position %e)" % (mname,pos,m.wm())
      m.move(pos)

def show_motors_pos(infile):
  f=open(infile,"r")
  lines = f.readlines()
  f.close()
  for l in lines:
    (mname,pos) = l.split(); pos=float(pos)
    print mname,pos

def find_motor_by_name(motor_obj,mname):
  """ returns first motor object with given name, returns None if not found"""

  motors=motor_obj.__dict__.keys()
  for m in motors:
    if isinstance(motor_obj.__dict__[m],(mmm.Motor,vvv.VirtualMotor)):
      ## make a list of motor to handle filt[1],filt[2], ...
      if ( not isinstance(motor_obj.__getattribute__(m),list) ):
        mlist = [motor_obj.__getattribute__(m)]
      else:
        mlist = motor_obj.__getattribute__(m)
      for mm in mlist:
  #      if (motor_obj.__getattribute__(mm).name == mname):
        if (mm.name == mname):
          return mm
          break
  return None




def tweak(motor,step=0.1,dir=1):
  
  help = "q = exit; up = step*2; down = step/2, left = neg dir, right = pos dir\n"
  help = help + "g = go abs, s = set"
  print "tweaking the motor"
  #print "tweaking motor %s (pv=%s)" % (motor.name,motor.pvname)
  print "current position :"+   str(motor.wm())

  if dir != 1 and dir != -1:
    print("direction needs to be +1 or -1. setting dir to 1")
    
  
  step = float(step)
  oldstep = 0
  k=KeyPress.KeyPress()
  while (k.isq() is False):
    if (oldstep != step):
      print "stepsize: %f" % step
      sys.stdout.flush()
      oldstep = step
    k.waitkey()
    if ( k.isu() ):
      step = step*2.
    elif ( k.isd() ):
      step = step/2.
    elif ( k.isr() ):
      motor.umvr(step)
    elif ( k.isl() ):
      motor.umvr(-step)
    elif ( k.iskey("g") ):
      print "enter absolute position (char to abort go to)"
      sys.stdout.flush()
      v=sys.stdin.readline()
      try:
        v = float(v.strip())
        motor.umv(v)
      except:
        print "value cannot be converted to float, exit go to mode ..."
        sys.stdout.flush()
    elif ( k.iskey("s") ):
      print "enter new set value (char to abort setting)"
      sys.stdout.flush()
      v=sys.stdin.readline()
      try:
        v = float(v[0:-1])
        motor.set(v)
      except:
        print "value cannot be converted to float, exit go to mode ..."
        sys.stdout.flush()
    elif ( k.isq() ):
      break
    else:
      print help
  print "final position: " +  str(motor.wm())


def tweak2d(xmotor,ymotor,step=0.1,dirx=1,diry=1):
  #tweaks two motors, at same time. Arrows indicate direction and +- changes stepsize"

  
  help = "q = exit; + = step*2; - = step/2, arrows = direction \n"
  

  if dirx != 1 and dirx != -1:
    print("direction needs to be +1 or -1. setting dirx to 1")
  if diry != 1 and diry != -1:
    print("direction needs to be +1 or -1. setting diry to 1")

  step = float(step)
  oldstep = 0
  k=KeyPress.KeyPress()
  while (k.isq() is False):
    if (oldstep != step):
      print "stepsize: %f" % step
      sys.stdout.flush()
      oldstep = step
    k.waitkey()
    if ( k.iskey("+") ):
      step = step*2.
    elif ( k.iskey("-") ):
      step = step/2.
    elif ( k.isr() ):
      xmotor.umvr(dirx*step)
    elif ( k.isl() ):
      xmotor.umvr(-dirx*step)
    elif ( k.isu() ):
      ymotor.umvr(diry*step)
    elif ( k.isd() ):
      ymotor.umvr(-diry*step)
    elif ( k.isq() ):
      break
    else:
      print help
  print("final positions: (" +  str(xmotor.wm())+","+str(ymotor.wm())+")")



#doesn't dump the motor current and encoder information, as this crashes the readback to the motors.uncomment if you want to save them once for reference

def dump_MMS_par(motor_pvlist):
  if (isinstance(motor_pvlist,str)):
    motor_pvlist = [motor_pvlist]
  pars = [
   'description'         , '.DESC',
   'acceleration'        , '.ACCL',
   'units (EGU)'         , '.EGU',
   'direction'           , '.DIR',
   'encoder step size'   , '.ERES',
   'Gear x Pitch'        , '.UREV',
   'User Offset (EGU)'   , '.OFF',
   'retry deadband (EGU)', '.RDBD',
   'Steps Per Rev'       , '.SREV',
   'Max speed (RPS)'     , '.SMAX',
   'Speed(RPS)'          , '.S',
   'Speed(UGU/S)'        , '.VELO',
   'base speed (RPS)'    , '.SBAS',
   'base speed (EGU/s)'  , '.VBAS',
   'backlash'            , '.BDST'
#   'run current (%)'     , ':RC',
#   'use encoder (:EE)'   , ':EE',
#   'encoder lines per rev (:EL)'   , ':EL'
  ]
  fields_desc=pars[::2]
  fields=pars[1::2]
  out=[]
  title1="pvname"
  title2="------"
  for f in fields_desc:
    title1 += ",%s" % f
  for f in fields:
    title2 += ",%s" % f
  out.append(title1)
  out.append(title2)
  for m in motor_pvlist:
    v=m
    for f in fields:
      try:
        vv=pypsepics.get( m + f)
      except:
        print m + f
        vv="?"
      v += ",%s" % vv
    out.append(v)
  return out

def _dump_motorlist_tofile(file,motorlist):
  f=open(file,'wb')
  for line in motorlist:
    f.write(line+'\n')
  f.close()

def dump_MMS_par_tofile(motpvlist,filename):
  pl=dump_MMS_par(motpvlist)
  _dump_motorlist_tofile(filename,pl)
    
def load_MMS_pars(cvsfile,verbose=False):
  f=open(cvsfile)
  lines = f.readlines()
  for i in range(len(lines)): lines[i]=lines[i].rstrip("\n")
  fields = lines[1];
  lines = lines[2:];
  fields = fields.split(",")[1:]
  for l in lines:
    ll=l.split(",")
    pvbase=ll[0]
    if pvbase.startswith("#"): continue
    values=ll[1:]
    for i in range(len(fields)):
      f   = fields[i]
      pvw = pvbase + f
      pvr = pvw
      if (f == ":SET_RC"): pvr = pvbase + ":RC"
      if (f == ":SET_EE"): pvr = pvbase + ":EE"
      if f.startswith("#"): continue
      if (values[i] != "?"):
        try:
          vv=float(values[i])
        except:
          vv=values[i]
        if (f==":SET_RC"):  vv=str(values[i]); # for some reason the run current must be a string !
        if (f==":SET_EE"):  vv=str(values[i]); # for some reason the use encoder must be a string !
        if (f==".DIR"):  vv=int(values[i]);
        if (f==".SREV"): vv=int(values[i]);
        try:
          cv = pypsepics.get(pvr)
          if (verbose):
            print "current value ", cv
            print "setting  ",pvw," to ",values[i],
          if (f==".S"): pypsepics.put(pvbase+".SMAX",vv)
          pypsepics.put(pvw,vv)
          if (verbose): print " done"
        except pyca.pyexc:
          print "FAILED TO set ",pvw," to ",values[i]
#        time.sleep(0.1)
        try:
          rv = pypsepics.get(pvr)
          if (verbose): print "readback ",pvr, "    " ,rv
        except pyca.pyexc:
          print "FAILED TO READBACK ",pvr
        if (rv != cv):
          print "!!!NOTE!!! The pv %s has changed from %s to %s" % (pvw,cv,rv)
 



def estimatedTimeNeededForMotion(deltaS,vBase,vFull,Acc):
  """ return the estimated time needed to complete a motion
      inputs:
         deltaS = how much is the motor going to move
         vBase  = starting speed (EGU/s)
         vFull  = full     speed (EGU/s)
         Acc    = acceleration   (EGU/s**2)"""
  deltaS = np.abs(deltaS)
  Acc = float(Acc)
  #print Acc
  vFull = float(vFull)
  #print vFull
  timeFullSpeed = (deltaS-(vFull**2-vBase**2)/Acc)/vFull
  if (timeFullSpeed > 0):
    tTot = 2*(vFull-vBase)/Acc+timeFullSpeed
  else:
    tTot = 2*(np.sqrt(vBase**2+Acc*deltaS)-vBase)/Acc
  return tTot
