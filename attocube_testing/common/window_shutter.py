# Bob Nagler, June 2012
# class that shutter on windows in mec


import pypsepics
import numpy as np
from utilities import estr

class Window_Shutter():

    '''Shutter class that control the pneumatic window shutters.
    
       shutter.status()  : returns the status
       shutter.open()    : opens the shutter
       shutter.close()   : closes the shutter
    '''
    
    def __init__(self, pv, name):
        self._pv = pv
        self._name=name

    def isopen(self):
        if pypsepics.get(self._pv)==0 : return True
        else : return False
        
    def status(self):
       '''Prints the status of the shutter.'''
       statstr=self._name +' is '
       if self.isopen() : statstr+=estr('open',color='yellow',type='normal')
       else:         statstr+=estr('closed',color='green',type='normal')
       return(statstr)

    def open(self):
       '''Opens the shutter.'''
       pypsepics.put(self._pv,0)

    def close(self):
       '''Closes the shutter.'''
       pypsepics.put(self._pv,1)
