"""
Epics archiver tools to read archiver data from different index files.
"""
import casiTools, casi, sys
import dateutil, datetime
import time as timemodule
import pylab as p
from tools import *
from utilities import printnow

class epicsarchive:
  def __init__(self,index_file_list=['/reg/d/pscaa/MEC/2012/master_index','/reg/d/pscaa/MEC/current_index']):
    self.index_file_list = index_file_list
    self.arch = []
    for archfile in self.index_file_list:
      tarch = casi.archive()
      tarch.open(archfile)
      self.arch.append(tarch)

  def _get_channel(self,PV):
    self.present_channel = []
    for tarch in self.arch:
      channel = casi.channel()
      tarch.findChannelByName(PV, channel)
      self.present_channel.append(channel)
  
  def _get_all_channel_values_string(self,channel):
    value = casi.value()
    channel.getFirstValue(value)
    val_string = []
    while value.valid():
      val_string.append(casiTools.formatValue (value))
      value.next()
    return val_string
  
  def _get_timeinterval_values(self,channel,datetime0,datetime1):
    value = casi.value()
    datetime0 = datetime0.strftime('%Y/%m/%d %H:%M:%S')
    isinarch = channel.getValueAfterTime(datetime0,value)
    val = []
    time = []
    while value.valid():
      val.append(value.get())
      time.append(dateutil.parser.parse(value.time()))
      if time[-1]>datetime1:
        break	      
      value.next()
    return [time,val] 

  def _get_all_values(self):
    val_string = []
    for tchan in self.present_channel:
      val_string.extend(self._get_all_channel_values_string(tchan))
    val_string.sort()
    data=p.zeros([p.np.shape(val_string)[0],2])
    n=0
    for s in val_string:
      ss = s.split('\t')
      d = dateutil.parser.parse(ss[0])
      if ss[1].isdigit():
        v = float(ss[1])
      else:
        v = p.nan
      data[n,:]=[p.date2num(d),v]
      n +=1
    return data

  def _get_timeinterval_values_from_arch(self,datetime0,datetime1):
    val = []
    time = []
    for tchan in self.present_channel:
      [ttime,tval] = self._get_timeinterval_values(tchan,datetime0,datetime1)
      val.extend(tval)    
      time.extend(ttime)
#    data = zeros([len(time),2])
#    data[:,0]=time
#    data[:,1]=val
#    data = np.sort(data.view([('',data.dtype)]*data.shape[1]),0).view(data.dtype)
    I = argsort(time)
    time = array(time)
    val = array(val)
    val = val[I]
    time = time[I]
    return [time,val]
  def plot_pv_archive_data(self,pv,time_selection=30):
    [t,x] = self.pv_archive_data(pv,time_selection)
    nfigure('Epics archive '+pv)
    plot(t,x,'k.-')
    p.ylabel(pv)

  def pv_archive_data(self,pv,time_selection=30):
    enddate = False
    if type(time_selection)==list:
      startdate=time_selection[0]
      enddate = time_selection[1]
    else:
      startdate=time_selection
    if not enddate:
      enddate = datetime.datetime.now()

    if type(startdate)==str:
      startdate = dateutil.parser.parse(startdate)
    else:
      startdate = datetime.datetime.now()-datetime.timedelta(days=startdate)
    if type(enddate)==str:
      enddate = dateutil.parser.parse(enddate)
    self._get_channel(pv)
    printnow("Extracting data from archive ...")
    [time,data] = self._get_timeinterval_values_from_arch(startdate,enddate)
    printnow(" done\n")
    return [time,data]

#  def pv_archive_data(self,pv,time_selection=[]):
#    enddate = False
#    if type(time_selection)==list:
#      startdate=time_selection[0]
#      enddate = time_selection[1]
#    else:
#      startdate=time_selection
#    if not enddate:
#      enddate = p.date2num(datetime.datetime.now())
#
#    if type(startdate)==str:
#      startdate = dateutil.parser.parse(startdate)
#      startdate = p.date2num(startdate)
#    if type(enddate)==str:
#      enddate = dateutil.parser.parse(enddate)
#      enddate = p.date2num(enddate)
#    self._get_channel(pv)
#    printnow("Extracting data from archive ...")
#    data = self._get_all_values()
#    printnow(" done\n")
#    flt = _filtvec(data[:,0],[startdate,enddate])
#    data = data[flt,:]
#    return data

def _filtvec(vec,lims):
  filtbool = ((vec>min(lims)) & (vec<max(lims)))
  return filtbool


