import pypsepics
import utilities
import time
from numpy import *
from time import time, sleep
from utilitiesMotors import tweak, tweak2d
from common import daq_zhou
from mecbeamline import mecElog
from common import linac
from common import xyzstage
from common.pv2motor import PV2Motor as pv2motor
from common.motor import Motor as psmotor
import os
import fileinput
lcls=linac.Linac()
from scipy.interpolate import interp1d

class vm(object):
    def __init__(self,X,Y,Z,alpha,beta,axis_number,name):
      self.X=X
      self.Y=Y
      self.Z=Z
      self.alpha=alpha
      self.beta=beta
      self.axis_number=axis_number #0 for x, 1 for y, 2 for z
      self.name=name
      self.Ry=array(((cos(alpha),0,sin(alpha)),(0,1,0),(-sin(alpha),0,cos(alpha))))
      self.Rx=array(((1,0,0),(0,cos(beta),sin(beta)),(0,-sin(beta),cos(beta))))
      self.iRy=array(((cos(alpha),0,-sin(alpha)),(0,1,0),(sin(alpha),0,cos(alpha))))
      self.iRx=array(((1,0,0),(0,cos(beta),-sin(beta)),(0,sin(beta),cos(beta))))
      

    def xyz(self):
      """ calculates the xyz virtual motor positions from the physical motors X,Y,Z

          mostly for internal use, but can be called externally.
      """
      return dot(dot(self.iRx,self.iRy),array((self.X.wm(),self.Y.wm(),self.Z.wm())))

    def XYZ(self,xyz_i):
      """ calculates the motor position based on the input of the desired virtual motor positions
      """
      return dot(dot(self.Ry,self.Rx),xyz_i)

    def wm(self):
      return self.xyz()[self.axis_number]
    
    def mv(self,value):
      xyz_i=self.xyz()
      xyz_e=xyz_i
      xyz_e[self.axis_number]=value
      XYZ_new=self.XYZ(xyz_e)
      self.Z.mv(XYZ_new[2])
      self.X.umv(XYZ_new[0])
      self.Y.umv(XYZ_new[1])

    def umv(self,value):
      xyz_i=self.xyz()
      xyz_e=xyz_i
      xyz_e[self.axis_number]=value
      XYZ_new=self.XYZ(xyz_e)
      self.Z.umv(XYZ_new[2])
      self.X.umv(XYZ_new[0])
      self.Y.umv(XYZ_new[1])
    
    def mvr(self,value):
      p=self.wm()
      self.mv(p+value)

    def umvr(self,value):
      p=self.wm()
      self.umv(p+value)

class targetPreset():
    def __init__(self,sampleName, configFileName="pci.cfg"):
        self.sampleName = sampleName
        self.tg = -1000
        self.hexx = -1000
        self.hexy = -1000
        self.hexz = -1000
        self.hexu = -1000
        self.hexv = -1000
        self.hexw = -1000
        self.basedir = os.path.split(os.path.abspath( __file__ ))[0]
        self.configFileName = self.basedir+'/'+ configFileName
        self.loadFromConfigFile()
        


    def set(self,tg=None,hex_x=None,hex_y=None,hex_z=None,hex_u=0,hex_v=0,hex_w=0):
        if tg == None and hex_x == None and hex_y == None and hex_z == None:
            tg = pypsepics.get('MEC:PCI:MMS:TG:S.RBV')
            hex_x = pypsepics.get('MEC:PCI:HEX:TG:Xpr:rbv')
            hex_y = pypsepics.get('MEC:PCI:HEX:TG:Ypr:rbv')
            hex_z = pypsepics.get('MEC:PCI:HEX:TG:Zpr:rbv')
            hex_u = pypsepics.get('MEC:PCI:HEX:TG:Upr:rbv') 
            hex_v = pypsepics.get('MEC:PCI:HEX:TG:Vpr:rbv')
            hex_w = pypsepics.get('MEC:PCI:HEX:TG:Wpr:rbv')

        flag = False
        for line in fileinput.input(self.configFileName,inplace=1):
            lineStripped = line.strip().split()
            lineStrippedStr = line.strip('\n')
            if len(lineStripped) == 0:
                print "%s" % lineStrippedStr
                continue
            if lineStripped[0] == self.sampleName:
                flag = True
                print "%s\t%s\t\t%s\t%s\t%s\t%s\t%s\t%s" % (self.sampleName,tg,hex_x,hex_y,hex_z,hex_u,hex_v,hex_w )
            else:
                print "%s" % lineStrippedStr
                
        if not flag:
            print "I do not find any preset positions for %s in %s, add a new line now!" % (self.sampleName, self.configFileName)
            fileForConfig = open(self.configFileName,"a")
            fileForConfig.write("%s\t%s\t\t%s\t%s\t%s\t%s\t%s\t%s" % (self.sampleName,tg,hex_x,hex_y,hex_z,hex_u,hex_v,hex_w))

    def get(self):
        fileForConfig = open(self.configFileName)
        flag = False
        for line in fileForConfig:
            listEachLine = line.strip().split()
            if len(listEachLine) == 0:
                continue
            token = listEachLine[0]
            if token == self.sampleName:
                flag = True
                tg,hexx,hexy,hexz,hexu,hexv,hexw = map(float, listEachLine[1:] )
                print "Position for %s is: target_scan = %s, hex_x = %s, hex_y = %s, hex_z = %s, hex_u = %s, hex_v = %s,hex_w = %s " % (self.sampleName, tg,hexx,hexy,hexz,hexu,hexv,hexw)
        if not flag :
            print "Preset positions for %s is not defined in the config file %s!" % (self.sampleName,self.configFileName)

    def __call__(self):
        self. loadFromConfigFile()
        if self.tg == -1000 and self.hexx == -1000 and self.hexy == -1000 and self.hexz == -1000 and self.hexu == -1000 and self.hexv == -1000 and self.hexw == -1000 :
            print "Preset positions for %s is not defined, will not start moving the sample stage!" % self.sampleName
        else:
            print "Start moving to %s now" % self.sampleName
            pypsepics.put('MEC:PCI:MMS:TG:S.VAL',self.tg)
            pypsepics.put('MEC:PCI:HEX:TG:Xpr',self.hexx)
            pypsepics.put('MEC:PCI:HEX:TG:Ypr',self.hexy)
            pypsepics.put('MEC:PCI:HEX:TG:Zpr',self.hexz)
            pypsepics.put('MEC:PCI:HEX:TG:Upr',self.hexu)
            pypsepics.put('MEC:PCI:HEX:TG:Vpr',self.hexv)
            pypsepics.put('MEC:PCI:HEX:TG:Wpr',self.hexw)

            # special care for pin position as it is offset by 1 mm in coarse X and Z from regular targets
	    # in the new target design, from september 2016, there is no more offset between pin and sample plan, so commenting those lines (E> Galtier)
#            if self.sampleName == 'ThickPin' or self.sampleName == 'ThinPin' :
#                pypsepics.put('MEC:PCI:MMS:TC:Z.VAL',6.68)
#                pypsepics.put('MEC:PCI:MMS:TC:X.VAL',95.23)
            
    def loadFromConfigFile(self):
        fileForConfig = open(self.configFileName)
        for line in fileForConfig:
            listEachLine = line.strip().split()
            if len(listEachLine) == 0:
                continue
            token = listEachLine[0]
            if token == self.sampleName:
               self.tg,self.hexx,self.hexy,self.hexz,self.hexu,self.hexv,self.hexw = map(float, listEachLine[1:] )

# this tightfocuslens class does some calculation of the transmission and focal length of the tight focusing lens            
class TightFocusingLens():
    def __init__(self):
        # tabulated dispersive decrement
        self.delta = {1000.:0.000352431, 2000.:0.0000862, 3000.:0.0000381, 4000.:0.0000214, 5000.:0.0000137, 6000.:9.48e-6,\
                                    7000.:6.96e-6,8000.:5.33e-6,9000.:4.21e-6,10000.:3.41e-6}
        # tabulated mass attenuation
        self.beta = {1000.:0.0000109, 2000.:6.8e-7,3000.:1.29e-7,4000.:3.92e-8,5000.:1.56e-8,6000.:7.35e-9,7000.:3.94e-9, \
                     8000:2.34e-9,9000.:1.5e-9,10000.:1.03e-9}
        # ev to Angstrom constant
        self.lambdaToE = 12398. # E(ev) * lambda(A) = 12398
        # thickness of lens, approximated values for all belens provided by vendor
        self.l = 7.e-4 # 700 um
        self.d = 60.e-6 # 60 um
        # constant distances
        self.distUndulatortoTCC = 410
        self.distIPM1toTCC = 76.37
        self.distIPM1toMECLens = 72.37

        xdelta= array(sorted(self.delta.keys()))
        ydelta= []
        for i in xdelta:      
            ydelta.append(self.delta[i])
        ydelta = array(ydelta)
        self.funcInterpolationDelta = interp1d(xdelta, ydelta )

        xbeta= array(sorted(self.beta.keys()))
        ybeta= []
        for i in xbeta:
            ybeta.append(self.beta[i])
        ybeta = array(ybeta)
        self.funcInterpolationBeta = interp1d(xbeta, ybeta )

    def computeSingleLensFocalLength(self, curvatureRadius = 1500.e-6, XRayEnergy=None):        
        if XRayEnergy:
            _XRayEnergy = XRayEnergy
        else:
            _XRayEnergy = lcls.getXrayeV()
        print "X-ray photon energy is %s " % _XRayEnergy

        # using Interpolation to get the delta and beta for different X-ray photon energy
        try:
            _delta = self.funcInterpolationDelta(_XRayEnergy)
            return curvatureRadius/2.0/_delta
            
        except ValueError:
            print "X-ray photon energy is beyond the interpolation range!"
        
        # 7200 ev, focus = 240.6mm source size = 0.06 mm, g = 400 m, Be, density = 1.845 g/cm^2
        # delta/rho, mu/rho
        # R = 0.05 mm, R0 = 0.15 mm
        # d = 0.03 mm
        # N = 16
        # W = 1.1mm


class PCI(object):
  def __init__(self,be_cx,be_hx,be_hy,be_cz,nanox,nanoy,nanoz,name):
    self._name   = name
    self.be_cx = be_cx
    self.be_hx = be_hx
    self.be_hy = be_hy
    self.be_cz = be_cz
    self.nanox=nanox
    self.nanoy=nanoy
    self.nanoz=nanoz
    self.vx=vm(be_hx,be_hy,be_cz,-0.0011132,0.0015519,0,'vx')
    self.vy=vm(be_hx,be_hy,be_cz,-0.0011132,0.0015519,1,'vy')
    self.vz=vm(be_hx,be_hy,be_cz,-0.0011132,0.0015519,2,'vz')
#    self.vx=vm(be_hx,be_hy,be_cz,-0.0011246,0.0015465,0,'vx')
#    self.vy=vm(be_hx,be_hy,be_cz,-0.0011246,0.0015465,1,'vy')
#    self.vz=vm(be_hx,be_hy,be_cz,-0.0011246,0.0015465,2,'vz')
    self.daq=daq_zhou.Daq(host="mec-console",platform=0)

    # tight focusing lens
    self.belens = TightFocusingLens()
    
    # target preset functions
    self.pci_YAG = targetPreset("YAG")
    self.pci_YAG2 = targetPreset("YAG2")
    self.pci_45YAG = targetPreset("45YAG")
    self.pci_Al = targetPreset("Alum")
    self.pci_Fe = targetPreset("Fe")
    self.pci_LaB6 = targetPreset("LaB6")
    self.pci_Grid =  targetPreset("Grid")
    self.pci_thickpin = targetPreset("ThickPin")
    self.pci_thinpin = targetPreset("ThinPin")
    self.pci_pinhole = targetPreset("PinHole")
    self.pci_cross = targetPreset("Cross")

    # pci target navigation
    self.pci_target_hexx = pv2motor("MEC:PCI:HEX:TG:Xpr","MEC:PCI:HEX:TG:Xpr:rbv","pci hexx")
    self.pci_target_hexy = pv2motor("MEC:PCI:HEX:TG:Ypr","MEC:PCI:HEX:TG:Ypr:rbv","pci hexy")
    self.pci_target_hexz = pv2motor("MEC:PCI:HEX:TG:Zpr","MEC:PCI:HEX:TG:Zpr:rbv","pci hexz")
    self.pci_target_tgx = psmotor("MEC:PCI:MMS:TG:S","pci tgx",home = "low")

    self.pci_target=xyzstage.X2YZStage(self.pci_target_hexx , self.pci_target_hexy , self.pci_target_hexz, self.pci_target_tgx ,ntgx=11.3,ny=0,ntgxd=0,nyd=3.0, name="pci target") 
#    self.pci_target=xyzstage.X2YZStage(self.pci_target_hexx , self.pci_target_hexy , self.pci_target_hexz, self.pci_target_tgx ,ntgx=11.3,ny=0,ntgxd=0,nyd=3.683, name="pci target") 
    


  def ptycho_z_scan(self,speed,number_images,direction=1.0,go_back=True,disconnect_daq=True):
    """speed needs to be a string, and in um/s"""
    dz=4 
    z_init=self.nanoz.wm()
    speed_i=self.nanoz.speed()
    z_target=z_init+dz*direction
    self.nanoz.speed(speed)
    self.nanoz.mv(z_target)
    self.daq.begin(number_images)
    #lcls.get_burst(number_images)
    self.daq.wait() 
    self.nanoz.mv(self.nanoz.wm())
    if go_back:
        self.nanoz.speed(speed_i)
        self.nanoz.umv(z_init)
    if disconnect_daq:
        self.daq.disconnect()

  def ptycho_2d_scan(self,stepsize_h,stepsize_z,number_steps,number_images,freq=120):
    """stepsizes in micron. The nanocube has units micron, also for speed.
       stepsize_h is the horizontal spacing of the images
       stepsize_z is the vertical spacing of the images
       number_steps is the number of horizontal steps.
       number_images is the number of images during the vertical motion  in each horizontal step.
       So the total number of images is number_step*number_images.
       you need to be in lcls burst mode, with the burst rate the same as the lcls ebeamrate
       the stepsize_z needs to be small enough, especially at 120Hz, otherwise the nanocube
       speed will be too large.
       the total area scanned is in horizontal stepsize_h*number_steps, and in vertical
       stepsize_z*number_images.
       After the scan, the nanocube moves back to it's initial position.
    """
    x_init=self.nanox.wm()
    z_init=self.nanoz.wm()
    
    #freq=lcls.get_ebeamrate()
    
    speed=str(stepsize_z*freq)
    x_step=stepsize_h
    

    for index in range(number_steps):
        print("starting z line "+str(index))
        self.ptycho_z_scan(speed,number_images,go_back=True,disconnect_daq=False)
        self.nanox.mvr(x_step)
        

    ### move back to initial positions and disconnect daq
    self.nanox.mv(x_init)
    self.nanoz.mv(z_init)
    self.daq.disconnect()
    
  def ptycho_snake(self,stepsize_h,stepsize_z,number_steps,number_images,freq=120,goback=True):
    """stepsizes in micron. The nanocube has units micron, also for speed.
       stepsize_h is the horizontal spacing of the images
       stepsize_z is the vertical spacing of the images
       number_steps is the number of horizontal steps.
       number_images is the number of images during the vertical motion  in each horizontal step.
       So the total number of images is number_step*number_images.
       you need to be in lcls burst mode, with the burst rate the same as the lcls ebeamrate
       the stepsize_z needs to be small enough, especially at 120Hz, otherwise the nanocube
       speed will be too large.
       the total area scanned is in horizontal stepsize_h*number_steps, and in vertical
       stepsize_z*number_images.
    """
    x_init=self.nanox.wm()
    z_init=self.nanoz.wm()
    
    #freq=lcls.get_ebeamrate()
    
    speed=str(stepsize_z*freq)
    x_step=stepsize_h
    
    dir=1  #initial direction

    for index in range(number_steps):
        print("starting z line "+str(index))
        self.ptycho_z_scan(speed,number_images,direction=dir,go_back=False,disconnect_daq=False)
        self.nanox.mvr(x_step)
        dir=dir*(-1)

    ### move back to initial positions and disconnect daq
    self.nanox.speed(1)
    self.nanoz.speed(1)
    if goback:        
        self.nanox.mv(x_init)
        self.nanoz.mv(z_init)

    self.daq.disconnect()



  def tycho_scan_stop_go(self,stepsize_h,stepsize_z,number_steps_h,number_steps_z,shot_number,goback=True,disconnect_daq=True):
    """does a 2d scan using stop and go motion of the nanocube"""
    shotlog =  ""  # a log of all shots taken
    shotlog += "X,Z,number of shots\n"
    xinit=self.nanox.wm()
    zinit=self.nanoz.wm()

    stepsize_x=stepsize_h
    

    zend=zinit+stepsize_z*number_steps_z
    print(str(zinit))
    print(str(zend))
    
    for cur_step in range(number_steps_h+1):
       for zpos in linspace(zinit,zend,number_steps_z+1):
           self.nanoz.umv(zpos)
           print("shooting at position = ("+ str(self.nanox.wm())+","+str(self.nanoz.wm())+") , number of shots : "+ str(shot_number))
           shotlog+=str(self.nanox.wm())+","+str(self.nanoz.wm())+","+str(shot_number)+"\n"
           self.daq.begin(shot_number)
           lcls.get_burst(shot_number)  
           self.daq.wait()                        
       self.nanox.umvr(stepsize_x)
       
    if goback:
        self.nanox.mv(xinit)
        self.nanoz.mv(zinit)

    if disconnect_daq: self.daq.disconnect()
    print shotlog
    mecElog.submit("ptychography stop-go scan: \n  "+shotlog,tag='ptychography')


        
  ##############################################################################################
  # preset functions or shortcut funtions
  # only use them after you have finished the mode change from PCI to Ptychography or vice versa
  #############################################################################################


  def go_to_pci_mode(self):
      
      #############################################################
      print "Are you sure you want to switch to PCI mode now? Y/[N]"
      token = raw_input()
      if token == 'Y':
          pass
      else:
          print "pci.go_to_pci_mode() aborted."
          return
      #############################################################

      #############################################################
      # check list:
      # step 1 retract the belens from target
      print "Going through the checklist for switching to PCI mode now:"
      print "\n"
      print "(a) Move the Be lens back away from target to 150 mm (middle of travel range)."
      belensZpos = float(pypsepics.get('MEC:PCI:MMS:BL:ZC.RBV'))
      if belensZpos > 150:
          print "Belens is not at the middle of the travel range now, proceed to move it to 150 mm now? Y/[N]"
          token = raw_input()
          if token == 'Y':
               pypsepics.put('MEC:PCI:MMS:BL:ZC.VAL',150.0)
               print 'moving.....'
               while( abs(pypsepics.get('MEC:PCI:MMS:BL:ZC.RBV')-150.0) > 0.4 ):
                   sleep(2)
          else:
              print "pci.go_to_pci_mode() aborted."
              return
      print "Belens at position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:BL:ZC.RBV')
      
      # step 2 lower target hexapod to -12.5 mm
      print "\n"
      print "(b) Lower the targer hexapod all the way to -12.5 mm. Proceed? Y/[N]"
      token = raw_input()
      if token == 'Y':
          pypsepics.put("MEC:PCI:HEX:TG:Ypr",-12.5)
          sleep(2)
          print 'moving.......'
          while(pypsepics.get('MEC:PCI:HEX:TG:moving') == 1):
              sleep(2)
          print "Target hexapod at position = %s now, (a) checked!" % pypsepics.get('MEC:PCI:HEX:TG:Ypr:rbv')
      else:
          print "pci.go_to_pci_mode() aborted."
          return

      # step 3 make sure beam stop is at X-, pinhole is at Y+, TG scan is at X-
      print "\n"
      print "(c) Make sure beam stop is at X-, pinhole is at Y+ and target scan is at X-."
      beamstopXpos = float(pypsepics.get('MEC:PCI:MMS:BS:X.RBV'))
      if abs(beamstopXpos+28.4) > 0.4:
          print "Beam stop is not at X- right now, proceed to move it to X- now? Y/[N]"
          token = raw_input()
          if token == 'Y':
               pypsepics.put('MEC:PCI:MMS:BS:X.VAL',-28.4)
               print 'moving.....'
               while( abs(pypsepics.get('MEC:PCI:MMS:BS:X.RBV')+28.4) > 0.4 ):
                   sleep(3)
          else:
              print "pci.go_to_pci_mode() aborted."
              return
      print "Beam stop at position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:BS:X.RBV')


      pinholeYpos = float(pypsepics.get('MEC:PCI:MMS:PH:Y.RBV'))
      if abs(pinholeYpos-0) > 0.4:
          print "Pin hole is not at Y+ right now, proceed to move it to Y+ now? Y/[N]"
          token = raw_input()
          if token == 'Y':
               pypsepics.put('MEC:PCI:MMS:PH:Y.VAL',0)
               print 'moving.....'
               while( abs(pypsepics.get('MEC:PCI:MMS:PH:Y.RBV')-0) > 0.4 ):
                   sleep(3)
          else:
              print "pci.go_to_pci_mode() aborted."
              return
      print "Pin hole at position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:PH:Y.RBV')
      

      
      TargetScanpos = float(pypsepics.get('MEC:PCI:MMS:TG:S.RBV'))
      if abs(TargetScanpos-0) > 0.4:
          print "Target scan is not at X- right now, proceed to move it to X- now? Y/[N]"
          token = raw_input()
          if token == 'Y':
               pypsepics.put('MEC:PCI:MMS:TG:S.VAL',0.0)
               print 'moving.....'
               while( abs(pypsepics.get('MEC:PCI:MMS:TG:S.RBV')-0) > 0.4 ):
                   sleep(3)
          else:
              print "pci.go_to_pci_mode() aborted."
              return
      print "Target scan is at position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:TG:S.RBV')

      # step 4 start to move coarse X and coarse Z now for the target
      print "\n"
      print "(d) Start to move coarse X and Z for the target now."
      print "Do you want to move target coarse Z to 5.68 now? Y/[N]"
      token = raw_input()
      if token == 'Y':
          pypsepics.put('MEC:PCI:MMS:TC:Z.VAL',5.68)
          print 'moving.....'
          while( abs(pypsepics.get('MEC:PCI:MMS:TC:Z.RBV')-5.68) > 0.4 ):
              sleep(3)
      else:
          print "pci.go_to_pci_mode() aborted."
          return
      print "Target coarse Z is at position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:TC:Z.RBV')


      print "Do you want to move target coarse X to 96.23 now? Y/[N]"
      token = raw_input()
      if token == 'Y':
          pypsepics.put('MEC:PCI:MMS:TC:X.VAL',96.23)
          print 'moving.....'
          while( abs(pypsepics.get('MEC:PCI:MMS:TC:X.RBV')-96.23) > 0.4 ):
              sleep(3)
      else:
          print "pci.go_to_pci_mode() aborted."
          return
      print "Target coarse X is at position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:TC:X.RBV')


      print "Do you want to move target scan to pin position now? Y/[N]"
      token = raw_input()
      if token == 'Y':
          pypsepics.put('MEC:PCI:MMS:TG:S.VAL',152.45)
          print 'moving.....'
          while( abs(pypsepics.get('MEC:PCI:MMS:TG:S.RBV')-152.45) > 0.4 ):
              sleep(3)
      else:
          print "pci.go_to_pci_mode() aborted."
          return
      print "Target scan is at pin position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:TG:S.RBV')
      

      print "Do you want to raise the target hexapod to the pin position now? Y/[N]"
      token = raw_input()
      if token == 'Y':
          pypsepics.put('MEC:PCI:HEX:TG:Xpr',0.0)
          pypsepics.put('MEC:PCI:HEX:TG:Ypr',-4.9)
          pypsepics.put('MEC:PCI:HEX:TG:Zpr',0.0)
          pypsepics.put('MEC:PCI:HEX:TG:Upr',0.0)
          pypsepics.put('MEC:PCI:HEX:TG:Vpr',0.0)
          pypsepics.put('MEC:PCI:HEX:TG:Wpr',0.0)
      else:
          pass
      
      
      print 'moving.......'
      sleep(1)
      while(pypsepics.get('MEC:PCI:HEX:TG:moving') == 1):
          sleep(2)

      print "Finally, we are in PCI mode now !!! We are now at pin position."



  def go_to_ptycho_mode(self):
      
      #############################################################
      print "Are you sure you want to switch to Ptychography mode now? Y/[N]"
      token = raw_input()
      if token == 'Y':
          pass
      else:
          print "pci.go_to_ptycho_mode() aborted."
          return
      #############################################################


      #############################################################
      # check list:
      # step 1 retract the belens from target
      print "Going through the checklist for switching to Ptychography mode now:"
      print "\n"
      print "(a) Move the Be lens back away from target to 150 mm (middle of travel range)."
      belensZpos = float(pypsepics.get('MEC:PCI:MMS:BL:ZC.RBV'))
      if belensZpos > 150:
          print "Belens is not at the middle of the travel range now, proceed to move it to 150 mm now? Y/[N]"
          token = raw_input()
          if token == 'Y':
               pypsepics.put('MEC:PCI:MMS:BL:ZC.VAL',150.0)
               print 'moving.....'
               while( abs(pypsepics.get('MEC:PCI:MMS:BL:ZC.RBV')-150.0) > 0.4 ):
                   sleep(2)
          else:
              print "pci.go_to_ptycho_mode() aborted."
              return
      print "Belens at position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:BL:ZC.RBV')


      # step 2 lower target hexapod to -12.5 mm
      print "\n"
      print "(b) Lower the targer hexapod all the way to -12.5 mm. Proceed? Y/[N]"
      token = raw_input()
      if token == 'Y':
          pypsepics.put("MEC:PCI:HEX:TG:Ypr",-12.5)
          sleep(2)
          print 'moving.......'
          while(pypsepics.get('MEC:PCI:HEX:TG:moving') == 1):
              sleep(2)
          print "Target hexapod at position = %s now, (a) checked!" % pypsepics.get('MEC:PCI:HEX:TG:Ypr:rbv')
      else:
          print "pci.go_to_ptycho_mode() aborted."
          return
      
      

      # step 3 make sure beam stop is at X-, pinhole is at Y+, TG scan is at X-
      print "\n"
      print "(c) Make sure beam stop is at X-, pinhole is at Y+ and target scan is at X-."
      beamstopXpos = float(pypsepics.get('MEC:PCI:MMS:BS:X.RBV'))
      if abs(beamstopXpos+28.4) > 0.4:
          print "Beam stop is not at X- right now, proceed to move it to X- now? Y/[N]"
          token = raw_input()
          if token == 'Y':
               pypsepics.put('MEC:PCI:MMS:BS:X.VAL',-28.4)
               print 'moving.....'
               while( abs(pypsepics.get('MEC:PCI:MMS:BS:X.RBV')+28.4) > 0.4 ):
                   sleep(3)
          else:
              print "pci.go_to_ptycho_mode() aborted."
              return
      print "Beam stop at position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:BS:X.RBV')


      pinholeYpos = float(pypsepics.get('MEC:PCI:MMS:PH:Y.RBV'))
      if abs(pinholeYpos-0) > 0.4:
          print "Pin hole is not at Y+ right now, proceed to move it to Y+ now? Y/[N]"
          token = raw_input()
          if token == 'Y':
               pypsepics.put('MEC:PCI:MMS:PH:Y.VAL',0)
               print 'moving.....'
               while( abs(pypsepics.get('MEC:PCI:MMS:PH:Y.RBV')-0) > 0.4 ):
                   sleep(3)
          else:
              print "pci.go_to_ptycho_mode() aborted."
              return
      print "Pin hole at position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:PH:Y.RBV')
      

      
      TargetScanpos = float(pypsepics.get('MEC:PCI:MMS:TG:S.RBV'))
      if abs(TargetScanpos-0) > 0.4:
          print "Target scan is not at X- right now, proceed to move it to X- now? Y/[N]"
          token = raw_input()
          if token == 'Y':
               pypsepics.put('MEC:PCI:MMS:TG:S.VAL',0.0)
               print 'moving.....'
               while( abs(pypsepics.get('MEC:PCI:MMS:TG:S.RBV')-0) > 0.4 ):
                   sleep(3)
          else:
              print "pci.go_to_ptycho_mode() aborted."
              return
      print "Target scan is at position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:TG:S.RBV')



      # step 4 start to move coarse X and coarse Z now for the target
      print "\n"
      print "(d) Start to move coarse X and Z for the target now."
      print "Do you want to move target coarse Z to 90.42 now? Y/[N]"
      token = raw_input()
      if token == 'Y':
          pypsepics.put('MEC:PCI:MMS:TC:Z.VAL',90.42)
          print 'moving.....'
          while( abs(pypsepics.get('MEC:PCI:MMS:TC:Z.RBV')-90.42) > 0.4 ):
              sleep(3)
      else:
          print "pci.go_to_ptycho_mode() aborted."
          return
      print "Target coarse Z is at position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:TC:Z.RBV')


      print "Do you want to move target coarse X to 12.80 now? Y/[N]"
      token = raw_input()
      if token == 'Y':
          pypsepics.put('MEC:PCI:MMS:TC:X.VAL',12.80)
          print 'moving.....'
          while( abs(pypsepics.get('MEC:PCI:MMS:TC:X.RBV')-12.80) > 0.4 ):
              sleep(3)
      else:
          print "pci.go_to_ptycho_mode() aborted."
          return
      print "Target coarse X is at position = %s now, checked !" % pypsepics.get('MEC:PCI:MMS:TC:X.RBV')

      print "Do you want to raise the target hexapod to the ptycho targets position now? Y/[N]"
      token = raw_input()
      if token == 'Y':
          pypsepics.put('MEC:PCI:HEX:TG:Xpr',0.0)
          pypsepics.put('MEC:PCI:HEX:TG:Ypr',-3.0)
          pypsepics.put('MEC:PCI:HEX:TG:Zpr',0.0)
          pypsepics.put('MEC:PCI:HEX:TG:Upr',0.0)
          pypsepics.put('MEC:PCI:HEX:TG:Vpr',0.0)
          pypsepics.put('MEC:PCI:HEX:TG:Wpr',0.0)
      else:
          pass
      
      
      print 'moving.......'
      sleep(1)
      while(pypsepics.get('MEC:PCI:HEX:TG:moving') == 1):
          sleep(2)

      print "Finally, we are in Ptycho mode now !!!"

      
      


  ##############################################################################################
  # preset functions or shortcut funtions
  # only use them after you have finished the mode change from PCI to Ptychography or vice versa
  ##############################################################################################

  def pci_go_to_first_pillar(self):
      print "Only use this function after you have finished switching mode to PCI, pci.go_to_pci_mode()"
      pypsepics.put("MEC:PCI:MMS:TC:Z.VAL",5.68)
      pypsepics.put("MEC:PCI:MMS:TC:X.VAL",96.23)
      pypsepics.put('MEC:PCI:MMS:TG:S.VAL',137.94)
      pypsepics.put('MEC:PCI:HEX:TG:Ypr',-10.5)
  
  # Belens tight focusing section

  def belens_set1(self):
      print "Only use this function after you have finished switching mode to PCI, pci.go_to_pci_mode()"
      pass
  
  def belens_set2(self):
      pypsepics.put("MEC:PCI:MMS:BL:XC.VAL",60.1)
      pypsepics.put("MEC:PCI:MMS:BL:ZC.VAL",200)
      pypsepics.put("MEC:PCI:HEX:BL:Xpr",0.226)
      pypsepics.put("MEC:PCI:HEX:BL:Ypr",0.616)
      pypsepics.put("MEC:PCI:HEX:BL:Zpr",0.0)
      pypsepics.put("MEC:PCI:HEX:BL:Upr",-0.13)
      pypsepics.put("MEC:PCI:HEX:BL:Vpr",-0.06)
      pypsepics.put("MEC:PCI:HEX:BL:Wpr",0.0)
