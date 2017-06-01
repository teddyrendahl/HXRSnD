import pycdb
import pydaq
import os

def getTypeID(mne="Opal1kConfig"):
  a=os.popen("cat /reg/g/pcds/package/ana/release/pdsdata/xtc/TypeId.hh | sed -n '/enum Type/,/NumberOf};/p'")
  lines=a.readlines()
  a.close()
  idx = -1
  for i in range(len(lines)):
    if (lines[i].find( "Id_%s" % mne ) > 0 ):
      idx = i-1
      break
  if (idx == -1):
    return None
  else:
    return hex(idx) 




class DaqConfig(object):
  def __init__(self,dbpath="/reg/g/pcds/dist/pds/mec/configdb/current"):
    self.db = pycdb.Db(dbpath)
   

  def __getPrincetonCfg(self,alias="PRINCETON_BURST"):
    typeid=0x20012
    xtclist=self.db.get(alias=alias,typeid=typeid)
#   xtclist=self.db.get(alias=alias,typeid=getTypeID("PrincetonConfig"))
    return xtclist

  def getPrinceton(self,alias="PRINCETON_BURST"):
    ret = []
    for f in self.__getPrincetonCfg(alias):
      ret.append( f.get() )
    return ret

  def getPrincetonExpTime(self,alias="PRINCETON_BURST",detn=0):
    cfgs = self.__getPrincetonCfg()
    if (detn+1 > len(cfgs) ):
      raise "Asked to change Princeton n %d but only %d Princeton(s) are defined" % (detn,len(cfgs))
    cfg = cfgs[detn]
    cfg_pars = cfg.get()
    return cfg_pars["exposureTime"]


  def setPrincetonExpTime(self,exptime,alias="PRINCETON_BURST",detn=0,commit=True):
    cfgs = self.__getPrincetonCfg()
    if (detn+1 > len(cfgs) ):
      raise "Asked to change Princeton n %d but only %d Princeton(s) are defined" % (detn,len(cfgs))
    cfg = cfgs[detn]
    cfg_pars = cfg.get()
    cfg_pars["exposureTime"] = exptime
    cfg.set(cfg_pars)
    self.db.set(alias,cfg)
    if (commit):
      self.db.commit()
