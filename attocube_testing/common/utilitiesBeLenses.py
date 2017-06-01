from periodictable import xsf
from periodictable import formula as ptable_formula
import numpy as np
from numpy import real, exp, pi,sqrt
import datetime
import os
import shutil
import pprint
import config

def setLensSetsToFile(sets_listOfTuples,filename=config.DEFAULT_LENS_SET):
  try:
    shutil.copy2(filename,os.path.split(filename)[0]+'sets_Be_'+datetime.datetime.now().strftime('%Y-%m-%d'))
  except:
    pass	 
  f=open(filename,'w')
  f.write(pprint.pformat(sets_listOfTuples))
  f.close()
  
def getLensSet(setnumber_topToBot,filename=config.DEFAULT_LENS_SET):
  f=open(filename)
  sets = eval(f.read())
  f.close()
  return sets[setnumber_topToBot-1]

def getAttLen(E,material="Be",density=None):
  """ get the attenuation length (in meter) of material (default Si), if no
      parameter is given for the predefined energy;
      then T=exp(-thickness/att_len); E in keV"""
  att_len = float(xsf.attenuation_length(material,density=density,energy=E))
  return att_len

def getDelta(E,material="Be",density=None):
  """ returns 1-real(index_of-refraction) for a given material at a given energy"""
  delta = 1-real(xsf.index_of_refraction(material,density=density,energy=E))
  return delta

def calcFocalLengthForSingleLens(E,radius,material="Be",density=None):
  """ returns the focal length for a single lens f=r/2/delta """
  delta = getDelta(E,material,density)
  f = radius/2./delta
  return f

def calcFocalLength(E,lens_set,material="Be",density=None):
  """ lens_set = (n1,radius1,n2,radius2,...) """
  num = []
  rad = []
  ftot_inverse = 0
  if type(lens_set) is int:
    lens_set = getLensSet(lens_set)
  for i in range(len(lens_set)/2):
    num = lens_set[2*i]
    rad = lens_set[2*i+1]
    ftot_inverse += num/calcFocalLengthForSingleLens(E,rad,material,density)
  return 1./ftot_inverse

def calcBeamFWHM(E,lens_set,distance = 4,material="Be",density=None,fwhm_unfocused=800e-6,printsummary=True):
  """ usage calcBeamFWHM(8, (2,200e-6,4,500-6) )
      calculate beam parameters at a given distance for a given 
      lens set and energy.
      Optionally some other parameters can be set
  """
  f = calcFocalLength(E,lens_set,material,density)
  lam = 1.2398/E*1e-9
  # the w parameter used in the usual formula is 2*sigma
  w_unfocused    = fwhm_unfocused*2/2.35
  # assuming gaussian beam divergence = w_unfocused/f we can obtain
  waist = lam/np.pi*f/w_unfocused
  rayleigh_range = np.pi*waist**2/lam
  size = waist*np.sqrt(1.+(distance-f)**2./rayleigh_range**2)
  if printsummary:
    print "FWHM at lens   : %.3e" % fwhm_unfocused
    print "waist          : %.3e" % waist
    print "waist FWHM     : %.3e" % (waist*2.35/2.)
    print "rayleigh_range : %.3e" % rayleigh_range
    print "focal length   : %.3e" % f
    print "size           : %.3e" % size
    print "size FWHM      : %.3e" % (size*2.35/2.)
  return size*2.35/2

def findZpos(E,lens_set,spotsizefwhm,material="Be",density=None,fwhm_unfocused=800e-6):
  """finds the two distances the be lens needs to be at to get the spotsize in the chamber center
     findzpos(E,lens_set,spotsizefwhm,material="Be",density=None,fwhm_unfocussed=200e-6)    """
  f = calcFocalLength(E,lens_set,material,density)
  lam = 1.2398/E*1e-9
  w_unfocused    = fwhm_unfocused*2/2.35
  waist = lam/np.pi*f/w_unfocused
  rayleigh_range = np.pi*waist**2/lam
  print "waist          : %.3e" % waist
  print "waist FWHM     : %.3e" % (waist*2.35/2.)
  print "rayleigh_range : %.3e" % rayleigh_range
  print "focal length   : %.3e" % f
  w=spotsizefwhm*2/2.35
  deltaz=rayleigh_range*np.sqrt((w/waist)**2 -1)
  z1=f-deltaz
  z2=f+deltaz
  return (z1,z2)

  
def findEnergy(lens_set,distance=4.,material="Be",density=None):
  """ usage findEnergy(lens_set ,distance =4 (in m) )
      finds the neergy that would focus at a given distance (default = 4m)
  """
  Emin = 1.
  Emax = 24. 
  E = (Emax+Emin)/2.
  absdiff =100
  while ( absdiff > 0.0001 ):
    fmin = calcFocalLength(Emin,lens_set,material,density)
    fmax = calcFocalLength(Emax,lens_set,material,density)
    E = (Emax+Emin)/2.
    f = calcFocalLength(E,lens_set,material,density)
    if ( (distance<fmax) and (distance>f) ):
      Emin = E
    elif ( (distance>fmin) and (distance<f) ):
      Emax = E
    else:
      print "somehow failed ..."
      break
    absdiff = abs(distance-f)
  print "Energy that would focus at a distance of %.3f is %.3f" % (distance,E)
  s = calcBeamFWHM(E,lens_set,distance,material,density)
  return E

def findRadius(E,distance=4.0,material="Be",density=None):
  """ finds the radius of curvature of the lens that would focus the energy at the distance
      usage:  findRadius(E,distance=4.0,material="Be",density=None)
  """
  delta = getDelta(E,material,density)
  radius=distance*2*delta
  return radius


def calcLensApertureRadius(radius,diskthickness=1e-3,apexdistance=30e-6):
  R0=sqrt(radius*(diskthickness-apexdistance))
  return R0

def calcTransForSingleLens(E,radius,material="Be",density=None,fwhm_unfocused=900e-6,diskthickness=1.0e-3,apexdistance=30e-6):
  """ Calculates the transmission for a single lens.
      Usage : calcTransForSingleLens(E,radius,material="Be",density=None,fwhm_unfocused=800e-6,diskthickness=1.0e-3,apexdistance=30e-6):
  """
  delta = getDelta(E,material,density)
  mu=1.0/getAttLen(E,material="Be",density=None)
  s=fwhm_unfocused/2.35482
  S=(s**(-2.0)+2.0*mu/radius)**(-0.5)
  R0=sqrt(radius*(diskthickness-apexdistance))
  Trans=(S**2/s**2)*exp(-mu*apexdistance)*(1-exp(-R0**2.0/(2.0*S**2)))
  return Trans


def calcTransLensSet(E,lens_set,material="Be",density=None,fwhm_unfocused=900e-6,diskthickness=1.0e-3,apexdistance=30e-6):
  """ Calcultes the transmission of a lens set.
      usage : calcTrans(E,lens_set,material="Be",density=None,fwhm_unfocused=900e-6)
      There is latex document that explains the formula. Can be adapted to use different thicknesses for each lens,
      and different apex distances, but this would require changing the format of lens_set, which would mean changing
      a whole bunch of other programs too.
  """
  
  apexdistance_tot = 0
  radius_total_inv=0
  radius_aperture=1.0 #this is an ugly hack: the radius will never be bigger than 1m, so will always be overwritten
  if type(lens_set) is int:
    lens_set = getLensSet(lens_set)
  for i in range(len(lens_set)/2):
    num = lens_set[2*i]
    rad = lens_set[2*i+1]
    new_rad_ap=sqrt(rad*(diskthickness-apexdistance))
    radius_aperture=min(radius_aperture,new_rad_ap)
    radius_total_inv+=num/rad
    apexdistance_tot+=num*apexdistance
  radius_total=1.0/radius_total_inv
  equivalent_disk_thickness=radius_aperture**2/radius_total+apexdistance_tot
  transtot=calcTransForSingleLens(E,radius_total,material,density,fwhm_unfocused,equivalent_disk_thickness,apexdistance_tot)
  return transtot
  

