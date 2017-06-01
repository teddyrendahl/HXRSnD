### Bob Nagler, August 2012
### All units are SI

import pypsepics
import utilities
from numpy import *
from time import time, sleep, asctime
from utilitiesMotors import tweak, tweak2d
from meclasers import *
from matplotlib import pyplot
import os
import cPickle as pickle
import config

_DEFAULT_CAL_DIR = config.BASE_DIR+'fsQswitch_calibration/'

class Qswitch(object):
  '''class that defines Qswitch settings.
     There Can right now only be 1 qswitch controlled by this class, since the location of the calibration files
     is hard coded in the init. This could be changed in future if more than 1 qswitch needs be controllable. The
     file energymeter.py has a CalibratedEnergyMeter class that implement something like this.
  '''
     
  def __init__(self,channel_pvbase='MEC:LAS:DDG:01:a',high_lim=1e-3,low_lim=0.0,name='sqwitch'):
    self._name   = name
    self._pvbase= channel_pvbase
    self._high_lim=high_lim
    self._low_lim=low_lim
    self._calDir=_DEFAULT_CAL_DIR # directory where the calibration is saved
    self._calfilename_raw='fsqswitchcal_current_raw'   # calibration file
    self._calfilename_param='fsqswitchcal_current_param'
    self._Evsdelay=([],[])
    self._avgEvsdelay=([],[])

    # defining parameters and read from disk
    self._t0=None                # Peak of timing, in seconds
    self._tmin=None              # lowest timing value measured in calibration
    self._Emax=None              # in Joule
    self._Emin=None              # lowest energy measured in calibration
    self._fitparam_Evsdelay=None
    self._fitparam_delayvsE=None
    self.load_parameters()
    
    
  def delay_abs(self,delay=None):
    '''reads back the delay, if no argument is passed, or sets delay when argument passed
       useage: .delay_abs()  : reads back absolute qswitch delay, in s
               .delay_abs(258.434e-6)  : sets delay to 258.434microseconds
                  checks wether delay is between the low_lim and high_lim
    '''
    if delay==None:
      delay_read=pypsepics.get(self._pvbase+'DelaySI')
      return float(delay_read[5:])
    else:
      if self._low_lim < delay < self._high_lim:
        pypsepics.put(self._pvbase+'DelayAO',delay)
      else: print('Delay outside of allowed range')

  def delay_rel(self,delay=None):
    '''Reads back the delay relative to t0, if no argument is passed, or sets delay when argument passed.
       The delay are positive whet the qswitch comes before the seed, so negative delays mean no amplification
       So delay_rel = t0 - delay_abs
       useage: .delay_rel()  : reads qswitch delay relative to t0, in s
               .delay_rel(10e-6)  : sets delay to 10microsec, so the qsw is fired 10us before t0
                  checks wether delay is between the low_lim and high_lim
    '''
    if delay==None:
      return self._t0 - self.delay_abs(None)
    else:
      delay_abs_set=self._t0-delay
      self.delay_abs(delay_abs_set)

  def time_out(self):
    '''time out the qswitch; no amplification in MPA'''
    self.delay_rel(-3e-6)

  def Emax(self):
    self.delay_abs(self._t0)

  def record_E_vs_delay(self,Emeter,delay_range,points_per_delay=2,dt_measure=2,show_plot=True,new=True,save=False):
      '''records a scan of an Energy meter vs qswitch delay.
          useage: record_E_vs_delay(self,Emeter,delay_range,points_per_delay=2,dt_measure=2,show_plot=True,new=True,save=False):
               delay_range=(begin_delay,end_delay,#of delays)
               delay are in seconds
               points_per_delay are the number of datapoints collected per delay
               dt_measure is the time the program sleeps between measurements
               if new=True, the program overwrites (in memory) the current ._Evsdelay
               if save=True, the ._Evsdelay is pickled to disk
      '''
      if new: self._Evsdelay=([],[]) 
      delays=linspace(delay_range[0],delay_range[1],delay_range[2])
      for delay in delays:
        self.delay_abs(delay)
        for index in range(points_per_delay):
          sleep(dt_measure)
          self._Evsdelay[0].append(delay)
          self._Evsdelay[1].append(Emeter.read())
          printnow('measuring ' + str(delay))
      if show_plot: self.show_E_vs_delay()
      if save: self.save2file_E_vs_delay()



  def save2file_E_vs_delay(self):
      '''Pickels the _Evsdelay data to disk. moves the previous one to a new file'''
      timestr=asctime()
      oldfile=self._calDir+self._calfilename_raw
      newfile=self._calDir+self._calfilename_raw+str(timestr)
      newfile=newfile.replace(' ','_')
      os.system('mv '+oldfile+' '+newfile)
      ## pickling the file
      f=open(self._calDir+self._calfilename_raw,'wb')
      pickle.dump(self._Evsdelay,f)
      f.close()
  

  def load_E_vs_delay(self,filename=None):
    '''unpickle _Evsdelay. if no filename is given, it takes the standard file(see init)'''
    if filename==None: filename=self._calDir+self._calfilename_raw
    f=open(filename,'rb')
    self._Evsdelay=pickle.load(f)
    f.close()

  def show_E_vs_delay(self):
        pyplot.plot(self._Evsdelay[0],self._Evsdelay[1])
        pyplot.show()


  def calc_avgE_vs_delay(self,show=True):
    '''calculates the average E of a delay, since the record function can take multiple data points per delay'''
    self._avgEvsdelay=([],[])
    repeats=self._Evsdelay[0].count(self._Evsdelay[0][0])
    dif_delays=size(self._Evsdelay[0])/repeats
    for index in range(dif_delays):
      self._avgEvsdelay[0].append(self._Evsdelay[0][repeats*index])
      self._avgEvsdelay[1].append(mean(self._Evsdelay[1][index*repeats:(index+1)*repeats]))
    if show:
       pyplot.plot(self._avgEvsdelay[0],self._avgEvsdelay[1])
       pyplot.show()


  def find_t0andEmax(self,update=False):
    '''find t0 and Emax the Emin t_delay_min (called tmin) in calibration curve ._avgE_vs_delay.
       if update=True it writes those values to ._t0 and ._Emax, ._tmin and ._Emin
       otherwise returns t0,Emax,tmin,Emin
    '''
    #find minimum energy, and time delay
    Emin=min(self._avgEvsdelay[1])
    tmin=min(self._avgEvsdelay[0])
    
    DifE=[]
    Eprev=self._avgEvsdelay[1][0]
    for En in self._avgEvsdelay[1]:
      DifE.append(En-Eprev)
      Eprev=En
    peak_index=DifE.index(min(DifE))-1 #this is the index of the peak of the Evsdelay curve
    if min(DifE)>0:
      print('delay does not span cut-off. peak cannot be found.')
    else:
      t0=self._avgEvsdelay[0][peak_index]-20e-9  # t0 is set 20ns back, to be sure its an the correct side of the peak
      Emax=self._avgEvsdelay[1][peak_index]
      if update:
        self._t0=t0
        self._Emax=Emax
        self._tmin=tmin
        self._Emin=Emin
      else: return t0,Emax,tmin,Emin
    

  def cut_Evsdelay_at_t0(self):
    '''cuts the ._Evsdelay curve at t0, for the fit'''
    index=0
    for delay in self._Evsdelay[0]:
      if delay <= self._t0: index+=1
    return (self._Evsdelay[0][0:index],self._Evsdelay[1][0:index])

  def fit_Evsdelay(self,show=True,update=False):
    '''fits the part of the Evsdelay curve that is before t0 with a 4th order polynomial.
       x=delays  fit(x)=E
       if update =  True, the values are saved in ._fitparam_Evsdelay.
    '''
    order=20 #the order of the fit. For saved parameters this should be 6(temp set to 20)
    cutEvsdelay=self.cut_Evsdelay_at_t0()        
    param=polyfit(cutEvsdelay[0],cutEvsdelay[1],order)
    Evsdelayfit=poly1d(param)
    if show:
      delays=linspace(cutEvsdelay[0][0],cutEvsdelay[0][-1],200)
      pyplot.plot(self._Evsdelay[0],self._Evsdelay[1],'o',delays,Evsdelayfit(delays))
      pyplot.show()
    if update:
      self._fitparam_Evsdelay=param

  def fit_delayvsE(self,show=True,update=False):
    '''fits the part of the Evsdelay curve that is before t0 with a 4th order polynomial.
       x=E fit(x)=delay
       if update = True, the values are saved in ._fitparam_delayvsE.
    '''
    order=3 #the order. For saved parameter this should be 6 (temp set to 20)
    cutEvsdelay=self.cut_Evsdelay_at_t0()        
    param=polyfit(cutEvsdelay[1],cutEvsdelay[0],order)
    delayvsEfit=poly1d(param)
    if show:
      Energies=linspace(cutEvsdelay[1][0],cutEvsdelay[1][-1],200)
      pyplot.plot(self._Evsdelay[0],self._Evsdelay[1],'o',delayvsEfit(Energies),Energies)
      pyplot.show()
    if update:
      self._fitparam_delayvsE=param


  def save_parameters(self):
    ''' pickles the fit parameters to disk, and moves the older ones to new file
        The pickled object is a list containing : (_t0, _Emax, _fitparam_Evsdelay,_fitparam_delayvsE)
    '''
    timestr=asctime()
    oldfile=self._calDir+self._calfilename_param
    newfile=self._calDir+self._calfilename_param+str(timestr)
    newfile=newfile.replace(' ','_')
    os.system('mv '+oldfile+' '+newfile)
    ##difine list to pickle
    pickle_list=(self._t0,self._tmin,self._Emax,self._Emin,self._fitparam_Evsdelay,self._fitparam_delayvsE)
    ## pickling the file
    f=open(self._calDir+self._calfilename_param,'wb')
    pickle.dump(pickle_list,f)
    f.close()

  def load_parameters(self,filename=None):
    '''unpickle _fit_param, if no filename is given, it takes the standard file(see init)
      The pickled object is a list containing : (_t0, _Emax, _fitparam_Evsdelay,_fitparam_delayvsE)
    '''
    if filename==None: filename=self._calDir+self._calfilename_param
    try:
     ## loading pickle list from disk 
     f=open(filename,'rb')
     pickle_list=pickle.load(f)
     f.close()
     ## unpacking the list in qswitch
     (self._t0,self._tmin,self._Emax,self._Emin,self._fitparam_Evsdelay,self._fitparam_delayvsE)=pickle_list
    except IOError: print('no parameter file found; parameters not loaded')


  def calc_E(self,delay):
    ''' calculates the Energy for a given absolute delay'''
    if self._tmin <= delay <=self._t0:
      func=poly1d(self._fitparam_Evsdelay)
      return func(delay)
    else:
      returnstring= 'delay outside of calibration range ('+str(self._tmin)+','+str(self._t0)+')'
      return returnstring
    
  def calc_delay(self,Energy):
    ''' calculates the absolute delay for a given Energy'''
    if self._Emin <= Energy <=self._Emax:
      func=poly1d(self._fitparam_delayvsE)
      return func(Energy)
    else:
      returnstring='Energy outside of calibration range ('+str(self._Emin)+','+str(self._Emax)+')'
      return returnstring
  
  def E(self,Energy=None):
    '''sets the qswitch for the required energy'''
    if Energy==None:
      delay=self.delay_abs()
      return self.calc_E(delay)
    else:
      delay=self.calc_delay(Energy)
      if type(delay)==str: print delay
      else: self.delay_abs(self.calc_delay(Energy))
    
    
    
        
    
  
      
      
      

  
