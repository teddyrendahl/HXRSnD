import pypsepics
from numpy import floor_divide
from time  import sleep
class EventSequencer:

  def __init__(self,local_iocbase="IOC:MEC:EVENTSEQUENCER",sequence_group=1):
    self.iocbase = "IOC:IN20:EV01:ECS"
    self.local_iocbase = local_iocbase
    self.sequence_group = sequence_group
    self.__mode = ["Once","Repeat N Times","Repeat Forever"]
    self.__status = ["Stopped","Waiting","Playing"]
    self.__beamrate="EVNT:SYS0:1:LCLSBEAMRATE"
    self.define_pvnames()

  def define_pvnames(self):
    g = self.sequence_group
    ioc = self.iocbase
    self.__pv_nsteps   ="%s_LEN_%d" % (ioc,g)
    self.__pv_playmode = "%s_PLYMOD_%d" % (ioc,g)
    self.__pv_playcount = "%s_PLYCNT_%d"  % (ioc,g)
    self.__pv_playcontrol = "%s_PLYCTL_%d"  % (ioc,g)
    self.__pv_playstatus = "%s_PLSTAT_%d" % (ioc,g)
    self.__pv_nrepeats_to_do  = "%s_REPCNT_%d"  % (ioc,g)
    self.__pv_total_count = "%s_TPLCNT_%d"   % (ioc,g)
    self.__pv_notify = "%s_SEQ_%d.PROC" % (ioc,g)

  def setnsteps(self,nsteps):
    pypsepics.put(self.__pv_nsteps,nsteps)  

  def getnsteps(self):
    return pypsepics.get(self.__pv_nsteps)  

  def __beamcode_at_step(self,stepn,eventcode):
    pvname = "%s:EC_%d:%02d" % (self.local_iocbase,self.sequence_group,stepn)
    pypsepics.put(pvname,int(eventcode))

  def __deltabeam_at_step(self,stepn,delta):
    pvname = "%s:BD_%d:%02d" % (self.local_iocbase,self.sequence_group,stepn)
    pypsepics.put(pvname,int(delta))

  def __comment_at_step(self,stepn,comment):
    pvname = "%s:EC_%d:%02d.DESC" % (self.local_iocbase,self.sequence_group,stepn)
    pypsepics.put(pvname,comment)

  def __deltafiducial_at_step(self,stepn,delta=0):
    pvname = "%s:FD_%d:%02d" % (self.local_iocbase,self.sequence_group,stepn)
    pypsepics.put(pvname,int(delta))

  def setstep(self,stepn,beamcode,deltabeam,fiducial=0,comment=""):
    print "Setting step #%d to beamcode %d, deltabeam %d, fiducial %d" % (stepn,beamcode,deltabeam,fiducial)
    self.__deltafiducial_at_step(stepn,fiducial)
    self.__deltabeam_at_step(stepn,deltabeam)
    self.__beamcode_at_step(stepn,beamcode)
    self.__comment_at_step(stepn,comment)

  def modeOnce(self):
    self.__setmode("Once")

  def modeNtimes(self,N=1):
    self.__setmode("Repeat N Times",N)

  def modeForever(self):
    self.__setmode("Repeat Forever")

  def __setmode(self,mode,Ntimes=1):
    pvname=self.__pv_playmode
    if (mode == "Once"):
      pypsepics.put(pvname,0)
    elif (mode == "Repeat N Times"):
      pypsepics.put(pvname,1)
      pypsepics.put(self.__pv_nrepeats_to_do,Ntimes)
    elif (mode == "Repeat Forever"):
      pypsepics.put(pvname,2)
    else:
      print "mode must be Once|Repeat N Tiems|Repeat Forever"
      return
    self.__notify()

  def __getnpulses_in_play(self):
    return pypsepics.get(self.__pv_playcount)

  def __getnrepeats_to_do(self):
    return pypsepics.get(self.__pv_nrepeats_to_do)

  def getmode(self):
    pvname=self.__pv_playmode
    ret=pypsepics.get(pvname)
    return self.__mode[ret]

  def start(self):
    self.__total_count = pypsepics.get(self.__pv_total_count)
    pypsepics.put(self.__pv_playcontrol,1)

  def stop(self):
    pypsepics.put(self.__pv_playcontrol,0)

  def status(self,verbose=True):
#    pvname = "IOC:IN20:EV01:ECS_PLSTAT_3"
    ret=pypsepics.get(self.__pv_playstatus)
    ret = self.__status[ret]
    if (verbose):
      print "Mode: %s" % self.getmode()
      print "Current status: %s" % ret
    else:
      return ret

  def wait(self,verbose=False):
#    pvname = "IOC:IN20:EV01:ECS_PLSTAT_3"
    ntodo  = self.__getnrepeats_to_do()
    mode = self.getmode()
    if (mode  == "Repeat N Times"):
      while ( (pypsepics.get(self.__pv_playstatus) != 0) or (pypsepics.get(self.__pv_total_count) < ntodo) ):
        n = self.__getnpulses_in_play()
        if (verbose):
          print "running (%d of %d) ...\r" % (n,ntodo)
        sleep(0.01)
      n = self.__getnpulses_in_play()
      if (verbose): print "done (%d) ...\r" % n
      return
    elif (mode == "Once"):
      while ( (pypsepics.get(self.__pv_playstatus) != 0) or (pypsepics.get(self.__pv_total_count) != self.__total_count+1) ):
        if (verbose):
          print "running (%d) ...\r" % (ntodo)
        sleep(0.01)
      if (verbose): print "done (%d) ...\r" % n
      return

  def burst_forever(self):
    self.modeForever()
    self.start()

  def stop_burst(self):
    self.stop()

  def __notify(self):
    # notify the machine EVG of the changes
    pvmachine = "IOC:IN20:EV01:ECS_SEQ_3.PROC"
    pypsepics.put(pvmachine,1)

