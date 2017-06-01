# Zhou Xing, Sep. 2014, added interfaces to control exposure time and period etc.
# Bob Nagler, June 2012
# class that defines a gigecamera, for MEC
# same classes (connectpv, gigeimage, etc.) written by Pavel Stoffel


import threading
from   scipy import misc
from   scipy.weave import inline
from   psp.Pv import Pv
import pypsepics
import pyca
import os
from matplotlib import pyplot as plt
import config


import numpy as np


def caget(pvname):
    pv = Pv(pvname)
    pv.connect(5.)
    pv.get(False, 5.)
    pv.disconnect()
    return pv.value

  
class ConnectedPv(Pv):
    def __init__(self, name, adata=None):
        Pv.__init__(self, name)
        self.connected = False
        self._name = name
        self.evt = threading.Event()
        if adata != None:
            self.set_processor(adata)
        self.connect()
        
    def __del__(self):
        if self.connected:
            self.disconnect()

    def connect(self):
        Pv.connect(self, timeout = 1.0)
        self.connected = True
        # self.monitor_cb = self.changed
        evtmask = pyca.DBE_VALUE | pyca.DBE_LOG | pyca.DBE_ALARM
        self.monitor(evtmask)
        pyca.flush_io()

    def disconnect(self):
        if self.connected:
            self.unsubscribe()

    def grabbed(self):
        self.evt.set()

    def wait(self):
        return self.evt.wait(1.0)

    def set_processor(self, a):
        support_code = """
            #line 55
            static unsigned char *img_buffer;
            static int            buf_size;
            static unsigned char *buf_end;
            static py::object     grab_cb;

            static void grab_image(const void* cadata, long count, size_t size, void* usr)
            {
                const unsigned char *data = static_cast<const unsigned char*>(cadata);

                if (count > buf_size)
                    count = buf_size;
                memcpy(img_buffer, data, count);
                grab_cb.call();
            }
        """
        code = """
            #line 72
            img_buffer = (unsigned char *)a;
            buf_size = nbytes;
            buf_end = img_buffer + nbytes;
            grab_cb = grabbed;

            void *func = (void*)grab_image;
            PyObject* pyfunc =  PyCObject_FromVoidPtr(func, NULL);
            return_val = pyfunc;
        """

        nbytes = a.nbytes
        grabbed = self.grabbed
        
        rv = inline(code, ['a', 'nbytes', 'grabbed'],
                    support_code = support_code,
                    force = 0,
                    verbose = 0)       

        self.processor = rv
        pyca.flush_io()


class GigEImage():
    def __init__(self, name, cambasename = None):
        self._name = name
        self._camname = cambasename
        self.size0 = pypsepics.get(name+':ArraySize0_RBV')
        self.size1 = pypsepics.get(name+':ArraySize1_RBV')
        self.size2 = pypsepics.get(name+':ArraySize2_RBV')
        #self.size0 = 512 
        #self.size1 = 512
        #self.size2 = 512

        # print "Size:  %d x %d x %d" % self.size0, self.size1, self.size2

    def grab(self):
        # get rid of the old implementation
        # old implementaiton of grab() function
        #if self.size0 == 3:
        #    a = np.empty( ( self.size2, self.size1, self.size0 ), dtype=np.uint8, order='C' )
        #else:
        #    a = np.empty( ( self.size1, self.size0 ), dtype=np.uint8, order='C' )
        # 
        #imgPv = ConnectedPv(self._name+':ArrayData', adata=a)
        #imgPv.wait()     # wait for the image to be grabbed
        #imgPv.disconnect()
        #return a
        
        # new implementation of grab() function
        imagePV = self._name + ":ArrayData"
        if self._camname is not None:
            imageSizeXPV = self._camname + ":SizeX_RBV"
            imageSizeYPV = self._camname + ":SizeY_RBV"
        else:
            print 'camera base PV name are not provided!'
            return np.array([[0,1],[2,3]])
        try:
            image = pypsepics.get(imagePV)
            imageSize = len(image)
            imageArray = np.array( image )
            imageSizeX = int( pypsepics.get(imageSizeXPV) ) 
            imageSizeY = int( pypsepics.get(imageSizeYPV) ) 
            print "Total length of the Image1:ArrayData %s, NumofCol (X) %s, NumofRow (Y) %s" % (imageSize, imageSizeX, imageSizeY)
            
        except:
            print "fetching PV for the gige camera failed!"
            return np.array([[0,1],[2,3]])

        # work around this ugly gige camera bug where X x Y does not equal to the total number of pixels
        numOfPixels =  imageSizeX*imageSizeY
        if numOfPixels != imageArray.shape[0]:
            print "Total pixel numbers != X size x Y size, something is wrong!"
            print "We get around this problem by just padding zeros with the missing rows or missing columns."
            imageArraynew = np.append( imageArray, np.zeros(numOfPixels-imageArray.shape[0]) ) 
            return imageArraynew.reshape( (imageSizeY,imageSizeX) )
        
        return imageArray.reshape((imageSizeY, imageSizeX))
        

    def save(self, data):
        misc.imsave('outfile.png', data)

class GigeCamera(object):
    ''' defines a camera. Has routines:
        init (pvname) : initializes
        grab() : grabs images into numpy array
        show() : shows this gui
        shape(): size of the camera (x,y)
    '''
    def __init__(self,pvname_cam_base,pvname_image,cameraname="gigecamera",soic_pv=None, index=None):
        self._pvname_image=pvname_image
        self._pvname_base=pvname_cam_base
        self._name=cameraname
        self._img=GigEImage(pvname_image,pvname_cam_base)
        self._pvgain=self._pvname_base+':Gain'
        self._pvperiod=self._pvname_base+':AcquirePeriod'
        self._pvtime=self._pvname_base+':AcquireTime'
        self._pvstartcollection=self._pvname_base+':Acquire'
        self._soic_pv=soic_pv
        self._viewerlauncher=None
        self._index = index

    def __call__(self):
        '''call the viewer '''
        self.viewer()
        

    def reset(self):
        '''resets the ioc of the camera, if the soic_pv is defined'''
        if self._soic_pv!=None:
            pypsepics.put(self._soic_pv+":SYSRESET",1)
        else: print("No SOIC pvname defined. Change self._soic_pv to correct iocname")
        

    def grab(self,show=None):
        ''' Grabs the image. Shows if show=True '''
        tmpdata=self._img.grab()
        if show is None:
            plt.imshow(tmpdata)
            plt.show()
            return
        else:
            #misc.imsave(show,tmpdata)
            return tmpdata

    def shape(self):
        tmpdata=self.grab()
        shp=np.shape(tmpdata)
        return shp

    def gain(self,gainval=None):
        '''set the gain of camera, or reads back gain if no value is passed'''
        if gainval==None:
            return pypsepics.get(self._pvgain+"_RBV")
        elif 0<=gainval<=32: pypsepics.put(self._pvgain,round(gainval))
        else: print('gain out of range (0,32)')

    def gfactor(self,factor):
        '''increases/decreases the gain such that the counts go up by factor'''
        gainval=20.0*np.log10(factor)
        gain_i=self.gain()
        gain_f=gain_i+gainval
        self.gain(gain_f)

    def viewer(self):
        """launches the gui viewer of the gige camera"""
        # old pyqt viewer
        if not self._index:
            os.system(config.gige_launcher+" "+self._pvname_base)
        # new pyqt viewer
        else:
            os.system(config.new_gige_launcher+" "+str(self._index))

    def start(self):
        """Starts collection"""
        pypsepics.put(self._pvstartcollection,1)

    def stop(self):
        """Stops collection"""
        pypsepics.put(self._pvstartcollection,0)
        
    def period(self, periodval=None):
        """Set the collection preriod"""
        if periodval==None:
            return pypsepics.get(self._pvperiod+"_RBV")
        elif 0<periodval<=10: pypsepics.put(self._pvperiod,periodval)
        else: print('period out of range (0,10)')              

    def exposuretime(self, expval=None):
        """Set the exposure time"""
        period=pypsepics.get(self._pvperiod+"_RBV")
        if expval==None:
            return pypsepics.get(self._pvtime+"_RBV")
        elif 0<expval<=period:
            pypsepics.put(self._pvtime,expval)
        else: print('exposure time out of range (0,%s)' % period)
