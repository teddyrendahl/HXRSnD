#! /usr/bin/env python

import threading
from   scipy.weave import inline
from   scipy import misc
from   psp.Pv import Pv
import pyca

import numpy as np


def caget(pvname):
    pv = Pv(pvname)
    pv.connect(1.)
    pv.get(False, 1.)
    pv.disconnect()
    return pv.value

def caput(pvname, value):
    pv = Pv(pvname)
    pv.connect(1.)
    pv.put(value, timeout=1.)
    pv.disconnect()

  
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
    def __init__(self, name):
        self._name = name
        self.size0 = caget(name+':ArraySize0_RBV')
        self.size1 = caget(name+':ArraySize1_RBV')
        self.size2 = caget(name+':ArraySize2_RBV')
        # print "Size:  %d x %d x %d" % self.size0, self.size1, self.size2

    def grab(self):
        if self.size0 == 3:
            a = np.empty( ( self.size2, self.size1, self.size0 ), dtype=np.uint8, order='C' )
        else:
            a = np.empty( ( self.size1, self.size0 ), dtype=np.uint8, order='C' )
        imgPv = ConnectedPv(self._name+':ArrayData', adata=a)
        imgPv.wait()     # wait for the image to be grabbed
        imgPv.disconnect()
        return a

    def save(self, data):
        misc.imsave('outfile.png', data)

def main():
    from matplotlib import pyplot as plt
    import matplotlib.cm as cm
    try:
        img = GigEImage('TST:GIGE:IMAGE1')
        # img = GigEImage('MEC:GIGE:IMAGE1')
        data = img.grab()
        # print data.nbytes
        # print data.shape
        if (data.ndim == 3):
            plt.imshow(data)                     # color image
        else:
            plt.imshow(data, cmap=cm.Greys_r)    # b/w as grayscale
        plt.show()

    except Exception, e:
        print 'Exception: %s' %(e)

if __name__ == '__main__':
    print 'Manufacturer: ' + caget('TST:GIGE:CAM1:Manufacturer_RBV')
    print 'Model: ' + caget('TST:GIGE:CAM1:Model_RBV')
    print 'MaxSizeX: %d' % caget('TST:GIGE:CAM1:MaxSizeX_RBV')
    print 'MaxSizeY: %d' % caget('TST:GIGE:CAM1:MaxSizeY_RBV')
    print 'ArraySizeX: %d' % caget('TST:GIGE:CAM1:ArraySizeX_RBV')
    print 'ArraySizeY: %d' % caget('TST:GIGE:CAM1:ArraySizeY_RBV')
    print 'ArraySizeZ: %d' % caget('TST:GIGE:CAM1:ArraySizeZ_RBV')
    # Exposure
    caput('TST:GIGE:CAM1:AcquireTime', 0.05)
    caput('TST:GIGE:CAM1:AcquirePeriod', 1)
    caput('TST:GIGE:CAM1:Gain', 10)
    # Region of Interest
    caput('TST:GIGE:CAM1:MinX', 0)
    caput('TST:GIGE:CAM1:MinY', 0)
    MaxSizeX = caget('TST:GIGE:CAM1:MaxSizeX_RBV') + 3 / 4
    MaxSizeY = caget('TST:GIGE:CAM1:MaxSizeY_RBV')
    caput('TST:GIGE:CAM1:SizeX', MaxSizeX)
    caput('TST:GIGE:CAM1:SizeY', MaxSizeY)
    # Binning
    caput('TST:GIGE:CAM1:BinX', 1)
    caput('TST:GIGE:CAM1:BinY', 1)
    # Image Mode: Continuous
    caput('TST:GIGE:CAM1:ImageMode', 2)
    # Trigger Mode:  Fixed Rate
    caput('TST:GIGE:CAM1:TriggerMode', 5)
    # Start
    caput('TST:GIGE:CAM1:Acquire', 1)
    #
    # Stop
    # caput('TST:GIGE:CAM1:Acquire', 0)
    main()
