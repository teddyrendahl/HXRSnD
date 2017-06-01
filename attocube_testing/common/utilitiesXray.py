""" Utilities to perfrom various calculations """

import numpy as n
import xraylib
import pypsepics
from utilitiesCalc import *

def index(ID,E=None):
  if E==None:
    E=pypsepics.get("SIOC:SYS0:ML00:AO627")/1000
  E=eV(E)/1000
  d=Density[ID]
  n_real=xraylib.Refractive_Index_Re(ID,E,d)  
  n_imag=xraylib.Refractive_Index_Im(ID,E,d)  
  n=complex(n_real,n_imag)
  return n

def Fi(ID,E=None):
  if E==None:
    E=pypsepics.get("SIOC:SYS0:ML00:AO627")/1000
  E=eV(E)/1000
  z=elementZ[ID]
  f=xraylib.Fi(z,E)  
  return f

def Fii(ID,E=None):
  if E==None:
    E=pypsepics.get("SIOC:SYS0:ML00:AO627")/1000
  E=eV(E)/1000
  z=elementZ[ID]
  f=xraylib.Fii(z,E)  
  return f

def CS_Total(ID,E=None):
  if E==None:
    E=pypsepics.get("SIOC:SYS0:ML00:AO627")/1000
  E=eV(E)/1000
  z=elementZ[ID]
  CS=xraylib.CS_Total(z,E)  
  CS=CS*AtomicMass[ID]/c['NA']/u['cm']**2
  return CS

def CS_Photo(ID,E=None):
  """Returns the total photoabsorption cross section in m^2
     ID is the element symbol
     E is the photon energy (default is current LCLS value)
  """
  if E==None:
    E=pypsepics.get("SIOC:SYS0:ML00:AO627")/1000
  E=eV(E)/1000
  z=elementZ[ID]
  CS=xraylib.CS_Photo(z,E)  
  CS=CS*AtomicMass[ID]/c['NA']/u['cm']**2
  return CS

def CS_Rayl(ID,E=None):
  """Returns the total Rayleigh (elastic) cross section in m^2
     ID is the element symbol
     E is the photon energy (default is current LCLS value)
  """
  if E==None:
    E=pypsepics.get("SIOC:SYS0:ML00:AO627")/1000
  E=eV(E)/1000
  z=elementZ[ID]
  CS=xraylib.CS_Rayl(z,E)  
  CS=CS*AtomicMass[ID]/c['NA']/u['cm']**2
  return CS

def CS_Compt(ID,E=None):
  """Returns the total Compton (inelastic) cross section in m^2
     ID is the element symbol
     E is the photon energy (default is current LCLS value)
  """
  if E==None:
    E=pypsepics.get("SIOC:SYS0:ML00:AO627")/1000
  E=eV(E)/1000
  z=elementZ[ID]
  CS=xraylib.CS_Compt(z,E)  
  CS=CS*AtomicMass[ID]/c['NA']/u['cm']**2
  return CS

def CS_KN(E=None):
  if E==None:
    E=pypsepics.get("SIOC:SYS0:ML00:AO627")/1000
  E=eV(E)/1000
  z=elementZ[ID]
  CS=xraylib.CS_KN(E)  
  return CS



