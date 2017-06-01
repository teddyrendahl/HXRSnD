""" Module that handles global variables
"""
import sys
import utilities
import os
import time

gVarsFolder = None

gVars=dict()

def checkFolder():
  """ returns (and set global variable) for folder to use for logfile
  most of the time it will be ~operator/pyps/log/"""
  beamline = utilities.guessBeamline()
  user     = "%sopr" % beamline
  base_folder   = os.path.expanduser("~%s" % user)
  # test writing permission
  can_write = os.access(base_folder,os.W_OK)
  if (can_write):
    folder = base_folder + "/pyps/vars/"
  else:
    folder = os.path.expanduser("~") + "/pyps/vars/"
  if ( not os.path.exists(folder) ): os.makedirs(folder)
  globals()["gVarsFolder"] = folder
  return folder

def VarToFilename(var):
  folder = gVarsFolder + "/" + var
  if ( not os.path.exists(folder) ): os.makedirs(folder)
  return folder + "/value"

def readFromMeM(var):
  if (var in gVars): return gVars[var]

def writeInMeM(var,value):
  g = globals()["gVars"]
  g[var]=value
 
def writeInFile(var,value):
  fname = VarToFilename(var)
  f = open(fname,"w")
  f.write("%s" % value)
  f.flush()
  f.close()

def readFromFile(var):
  fname = VarToFilename(var)
  f = open(fname,"r")
  a = f.read()
  f.close()
  return a

def writeMemInFiles():
  keys = gVars.keys()
  for k in keys:
    v=readFromMeM(k)
    writeInFile(k,v)
    

checkFolder()
