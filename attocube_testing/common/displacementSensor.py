import numpy as np
import pylab as pl
import pypsepics
import tools
from time import sleep
import datetime
import KeyPress
import Plot
class discplacementSensor(object):
  def __init__(self,AIpv="XPP:R31:IOC:21:ai0:in8.VAL",poslims=(-5,5),voltlims=(-10,10),name=''):
    self.pv = AIpv
    self.poslims = poslims
    self.voltlims = voltlims
    self.name = name

  def updatingplot(self,sleeptime=.1,figurename="Displacementsensor",noofpoints = 50,showpos=True):
    update=True
    pl.ion()
    plt = Plot.Plot2D(10,windowtitle='Displacement Sensor')
    plt.set_xlabel('Time')
    plt.set_ylabel('Position / mm')
    
    val = []
    tt = []
    pos = []

    quit = KeyPress.KeyPress(esc_key="q")
    while not quit.isq():   
      tval = pypsepics.get(self.pv)
      val.append(tval)
      pos.append(self.poslims[0]+tval*(np.diff(self.voltlims)/np.diff(self.poslims)))
      tt.append(datetime.datetime.now())
      tt = tt[-100:]
      pos = pos[-100:]
      val = val[-100:]
      if showpos:
        plt.setdata(tt,pos)
      else:
        pl.gca().lines[-1].set_ydata(val[-noofpoints:])
        pl.gca().lines[-1].set_xdata(tt[-noofpoints:])
      sleep(sleeptime)
      pl.draw()
      #c=KeyPress.getc()
      #if (c=="q"):
        #print "exiting"
        #break

  def updatingplot_old(self,sleeptime=.2,figurename="Displacementsensor",noofpoints = 100,showpos=True):
    update=True
    val = [0]
    tt = [datetime.datetime.now()]
    pos = [0]
    pl.ion()

    tools.nfigure(figurename)
    if showpos:
      lh = pl.plot(tt[-noofpoints:],pos[-noofpoints:],'ko-')
      pl.xlabel('Time')
      pl.ylabel('Position / mm')
    else:                
      lh = pl.plot(tt[-noofpoints:],val[-noofpoints:],'ko-')
      pl.xlabel('Time')
      pl.ylabel('Volt / mm')
    pl.draw()
    lh = pl.gca().lines[0]
    val = []
    tt = []
    pos = []
    quit = KeyPress.KeyPress(key="q")
    while quit.isq() is not True:   
      tval = pypsepics.get(self.pv)
      val.append(tval)
      pos.append(self.poslims[0]+tval*(np.diff(self.voltlims)/np.diff(self.poslims)))
      tt.append(datetime.datetime.now())
      tt = tt[-noofpoints:]
      pos = pos[-noofpoints:]
      if showpos:
        pl.gca().lines[-1].set_ydata(pos[-noofpoints:])
        pl.gca().lines[-1].set_xdata(tt[-noofpoints:])
        print pos,tt
      else:
        pl.gca().lines[-1].set_ydata(val[-noofpoints:])
        pl.gca().lines[-1].set_xdata(tt[-noofpoints:])
      sleep(sleeptime)
      pl.draw()
      #c=KeyPress.getc()
      #if (c=="q"):
        #print "exiting"
        #break

