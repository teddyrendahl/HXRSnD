### Bob Nagler, August 2012
### All units are SI
### Module that contains some definitions for energy meters.

import config
import pypsepics
import utilities
import time
from numpy import *
from time import time, sleep
from utilitiesMotors import tweak, tweak2d
import os
import cPickle as pickle
from matplotlib import pyplot

class EnergyMeter(object):
  '''class that defines an Energy meter.
     Useage: emeter() returns the value (in Joule) on the meter
  '''

  def __str__(self):
    return "%s is as energy meter".format(self._name)

  def __init__(self,pv_name,name=None):
    self._pvname=pv_name
    self._name=name
    self._desc="An energy meter"
   

  def __call__(self):
    """ Shortcut, cals read: emeter.read() """
    return self.read()

  def read(self):
    return self.read_raw()

  def read_raw(self):
    return pypsepics.get(self._pvname)
  
class CoherentEnergyMeter(EnergyMeter):
  '''class that defines a Coherent Energy meter.
     These meters return the unit when read, which needs to be parsed.
     They have absolute calibration, so dont have a calibration routine.
     Useage: emeter() returns the value (in Joule) on the meter
     It has limited support for units, but probably not robust.
  '''

  def __init__(self,pv_name,name=None):
    EnergyMeter.__init__(self,pv_name,name)
    self._desc='An coherent energy meter'
 
  def read_raw(self):
    intstr=('0','1','2','3','4','5','6','7','8','9')
    rb=pypsepics.get(self._pvname)
    counter=0
    last_integer=0
    for ch in rb:
      if ch in intstr: last_integer=counter
      counter+=1
    first_unit=last_integer+1
    unit=rb[first_unit:]
    value=float(rb[0:first_unit])
    ### some simple unit parsing:
    factor=1.0
    if 'mJ' in unit: factor=1e-3
    elif 'uJ' in unit: factor=1e-6
    elif 'J' in unit: factor=1.0
    else: print('no unit, returns in a.u.')
    energy=value*factor
    return energy

  def unit(self):
    intstr=('0','1','2','3','4','5','6','7','8','9')
    rb=pypsepics.get(self._pvname)
    counter=0
    last_integer=0
    for ch in rb:
      if ch in intstr: last_integer=counter
      counter+=1
    first_unit=last_integer+1
    unit=rb[first_unit:]
    value=float(rb[0:first_unit])
    ### some simple unit parsing:
    factor=1.0
    if 'mJ' in unit: factor=1e-3
    elif 'uJ' in unit: factor=1e-6
    elif 'J' in unit: factor=1.0
    else: print('no unit, returns in a.u.')
    energy=value*factor
    return unit

class CalibratedEnergyMeter(EnergyMeter):
  '''class that defines an energymeter that has a calibration attached to it.
     The calibration is stored in a file on disk, in the location xxx
     It is a pickled set of parameters that map the reading on the meter to J in
     a specific position.
     You can have two meters which correspond to the same physical meter, but which
     have different calibrations. For the same physical meter would give you the
     energy after the MPA or in the target chamber. These would be different instances,
     which would have different calibration, but which read the same epics PV to gt
     a reaing.
     If no calibration is found on file, unity will be used.
     In general, the calibration should be linear to be reliable, but changing the
     order will be allowed (at your own risk; kids dont try this at home).
  '''

  
  def __init__(self,pv_name,name):
    '''gets the calibration data from disk. If it doesnt exist, it creates the
       right directory, and puth a unity calibration in there. This meter needs
       to have a name to correctly create the directory. As standard in MEC Python
       the name should be the same as the instance name.
    '''
    EnergyMeter.__init__(self,pv_name,name)
    self._desc='A calibrated energy meter'
    self._dir=config.calibrationdata_directory+'/'+name
    self._filename='energymeter_cal_current.pkl'

    ### checking whether the calibration data exists. If not a unity calibration is created.
    if not os.path.exists(self._dir):
      print("No calibration data directory exist. Creating directory; Calibration is set to unity.")
      os.makedirs(self._dir)
      self.save_param_to_file(param=[1.0,0.0])

    if not os.path.exists(self._dir+self._filename):
      print("No calbiration file found. Creating file; Calbration set to unity")
      self.save_param_to_file(param=[1.0,0.0])

    ### Reading the calibration file
    self.load_param_from_file()

  def calibrate_raw_reading(self,value):
    '''Translates between the raw detector value, and the actual calibrated value use the calibration parameter'''
    func=poly1d(self._param)
    return func(value)

  def read(self):
    return self.calibrate_raw_reading(self.read_raw())

  def calibrate_meter(self,ref_meter,energy_control,control_range,shots_per_control_position=2,fit_order=1,show=True,update=False,save_to_file=False,waittime=0.0):
    '''function that calibrates the energy meter.
       ref_meter is an energy meter agains which the meter is calibrated.
       energy_control is the object that control the energy, and energy_range the range (begin,end,#steps) in
       which control changes. So if x is a value in between begin and end, the energy_control(x) should set
       the energy. Note that the range is not the energy: it is simple the value that is passed to the energy control.
       This could be for example the motor position of an iris that is used to change the intensity. Waittime is the wait after changing the control, if for example you calibrate with a slow cohorent energymeter set to 2.0
    '''
    control_positions=linspace(control_range[0],control_range[1],control_range[2])
    y_Eref=[] #array in which the references energies will be saved
    x_Ecal=[] #array in which the to be calibrated meter values will be saved

    ### recording the Y vs X graph
    for control_pos in control_positions:
      energy_control(control_pos)
      for shot_number in range(shots_per_control_position):
        y_Eref.append(ref_meter.read())
        x_Ecal.append(self.read_raw())
        sleep(waittime)

    ### fitting the Y vs X with polynomial
    fit_param=polyfit(x_Ecal,y_Eref,fit_order)

    ### Plotting the result
    if show:
      func_Eref=poly1d(fit_param)
      Ecals=linspace(x_Ecal[0],x_Ecal[-1],200)
      pyplot.plot(x_Ecal,y_Eref,'o',Ecals,func_Eref(Ecals))
      pyplot.show()

    ### Updating the current parameters:
    if update:
      self._param=fit_param

    ### save params to file
    if save_to_file:
      self.save_param_to_file(param=fit_param)

    return fit_param

  def load_param_from_file(self):
    '''un pickles self._param from file'''
    file=open(self._dir+self._filename,'rb')
    self._param=pickle.load(file)
    file.close()
    

  def save_param_to_file(self,param=None):
    '''pickles self._param to file in appropriate place'''
    if param==None: param=self._param
    try:
      file=open(self._dir+self._filename,'wb')
      pickle.dump(param,file)
      file.close()
    except IOError:
      print("cannot save the parameter file. Probably the filename or directory don't exist.")

 

class CalibratedCoherentEnergyMeter(CalibratedEnergyMeter,CoherentEnergyMeter):
  '''This is a coherent energy meter that can be calibrated. For example the energymeter
     after the MPA can be calibrated to read the energy in the target chamber.'''
  def __init__(self,pv_name,name):
    CalibratedEnergyMeter.__init__(self,pv_name,name)    
    self._desc='A calibrated coherent energy meter'    
