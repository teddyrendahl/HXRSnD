from numpy import *
from matplotlib import pyplot, image
from scipy.optimize import leastsq
from scipy.stats import norm
import cPickle as pickle
import time
from time import asctime
import KeyPress
import config
import wx
from mecfunctions import unpickle, round2





class Beam(object):
    """ class of a laser beam spot.

        basic data type that hold the image as a 2D numpy array
    """
    def __init__(self,filename=None,name=None,cal=None,pulselength=None,energy=None,landa=800e-9,z=None):
        if name!=None:self.__name=name
        else:self.__name="laser spot"

        if filename!=None:
            self.__img=image.imread(filename)
            self.__original=self.__img
        else:
            self.__img=array([[0.0,0.0],[0.0,0.0]])
            self.__original=self.__img

        self.__tmp=array([[0.0,0.0],[0.0,0.0]]) #temporary array for intermediate calcs

        self.__bgimage=None #temporary array for intermediate calcs
        
        if cal!=None: self.__cal=cal # in m/pixel. SI
        else: self.__cal=1e-6
        
        if pulselength!=None: self.__pulselength=pulselength
        else: self.__pulselength=50e-15 ## pulse length in s, fwhm

        if energy!=None: self.__energy=energy
        else: self.__energy=0.1## pulse energy in Joule

        if z!=None: self.__z=z
        else: self.__z=0.0 ##z position in focal scan where image has been taken

        self.__landa=landa
        self._save_dir=config.scandata_directory+"/"

    def landa(self,l=None):
        '''reads or write landa'''
        if  l==None : return self.__landa
        else: self.__landa=l

    def z(self,zpos=None):
        '''reads or writes the z position'''
        if zpos==None: return self.__z
        else: self.__z=zpos

    def energy(self,en=None):
        '''reads or writes the energy of the beam'''
        if en==None: return self.__energy
        else: self.__energy=en

    def pulse_length(self,pl=None):
        '''reads or writes the pulse length'''
        if pl==None: return self.__pulselength
        else:self.__pulselength=pl

    def flux(self):
        '''normalizes the image, such that the values are the flux in J/m^2'''
        self.normalize()
        self.__img=self.__img*self.__energy/self.__cal**2

    def intensity(self):
        '''normalizes the image, such that the values are the intensity in W/m^2
           the magic number is 2*1.17 / sqrt(2*pi), with 1.17 the conversion from FWHM to w.
           this is sincet he pluse with is given in FWHM
        '''
        self.flux()
        self.__img=self.__img*0.939437/self.__pulselength
    
    def imread_file(self,filename):
        self.__original=image.imread(filename)+0.0
        self.__img=self.__original+0.0

    def imread(self,image):
        self.__original=image+0.0
        self.__img=image+0.0
        

    def cal(self,m_per_pix=None):
        '''reads or set the calibration in meters/pix'''
        if m_per_pix==None: return self.__cal
        else: self.__cal=m_per_pix

    def shape(self):
        return self.__img.shape

    def export(self):
        return self.__img

    def name(self,newname=False):
        if not newname: print self.__name
        else: self.__name=newname
    
    def show(self,in_pix=False):
        pyplot.imshow(self.__img)
        pyplot.title('z = '+str(self.z()))
        pyplot.colorbar()
        if not in_pix:
            tcks=self.calc_ticks()
            pyplot.xticks(tcks[0],tcks[1])
            pyplot.yticks(tcks[2],tcks[3])
        pyplot.show()

    def show_bg(self):
        '''shows the background image. always in pixels'''
        if self.__bgimage==None: print('No background image available')
        else:
          pyplot.imshow(self.__bgimage)
          pyplot.title('Background Image')
          pyplot.colorbar()
          pyplot.show()

    def calc_ticks(self,number_of_ticks=5.0):
        tick_space_lab=round2(self.shape()[0]*self.__cal/number_of_ticks,1)
        tick_space_loc=tick_space_lab/self.__cal
        mx=self.mx()
        my=self.my()
        xt_loc=linspace(mx-tick_space_loc*(number_of_ticks-1)/2.0,mx+tick_space_loc*(number_of_ticks-1)/2.0,number_of_ticks)
        yt_loc=linspace(my-tick_space_loc*(number_of_ticks-1)/2.0,my+tick_space_loc*(number_of_ticks-1)/2.0,number_of_ticks)
        xt_lab=linspace(-tick_space_lab*(number_of_ticks-1)/2.0,tick_space_lab*(number_of_ticks-1)/2.0,number_of_ticks)
        yt_lab=linspace(-tick_space_lab*(number_of_ticks-1)/2.0,tick_space_lab*(number_of_ticks-1)/2.0,number_of_ticks)
        
        return (xt_loc,xt_lab,yt_loc,yt_lab)
        

    def show_original(self):
        pyplot.imshow(self.__original)
        pyplot.colorbar()
        pyplot.show()

    def bgsubtract(self,refsquare=(1,20,1,20),bgimage=None,threshold=False,method='avg'):
        if method not in ('avg','threshold','bgimage'):
            print 'bg subtracting method unknown'
            return 
        if method == 'avg':
            avglevel=self.__img[refsquare[0]:refsquare[1],refsquare[2]:refsquare[3]].mean()
            self.__img=self.__img - avglevel
        if method =='threshold':
            if threshold==False:
                threslevel=self.__img[refsquare[0]:refsquare[1],refsquare[2]:refsquare[3]].max()
            else:
                threslevel=threshold
            self.__img=where(self.__img-threslevel>0,self.__img-threslevel,0)
        if method=='bgimage':
            ''' uses an image for the background subtract. If an image is passed in the function, that one is used. If None
                is passed, the one that is in the .__bgimage is used; if .__bgimage is None, the function reports a fail.
            '''
            if bgimage!=None:
                self.__img=self.__img - bgimage
            elif self.__bgimage!=None:
                self.__img=self.__img - self.__bgimage
            else: print("No background image passed or available")   
            

    def revert(self):
        """ go back to original image (last read or grabbed)"""
        self.__img=self.__original

    def normalize(self):
        ''' normalizes image, in the sense that the total integral equals 1'''
        self.__img=self.__img / self.__img.sum()
       
    def switch(self):
        '''switches the image, and the temporary image'''
        sw=self.__img
        self.__img=self.__tmp
        self.__tmp=sw

    def to_tmp(self):
        '''pushes image to tmp image'''
        self.__tmp=self.__img

    def mx(self):
        ''' return the mean in x direction of image.In pixels. '''
        tmp=self.__img        
        xpixs=self.__img.shape[1] #number of x pixels (columns)
        ypixs=self.__img.shape[0] # number of y pixels (rows)
        self.normalize()
        matx=tile(arange(1,xpixs+1),(ypixs,1)) #make a matrix with all rows = (1,2, .. 780)
        xfxy=matx*self.__img
        meanx=xfxy.sum()
        self.__img=tmp
        return meanx

  
    
    def my(self):
        ''' return the mean in y direction of image. In pixels '''
        tmp=self.__img
        xpixs=self.__img.shape[1] #number of x pixels (columns)
        ypixs=self.__img.shape[0] # number of y pixels (rows)
        self.normalize()
        maty=transpose(tile(arange(1,ypixs+1),(xpixs,1))) #make a matrix with all columns = (1,2, .. 780)
        yfxy=maty*self.__img
        meany=yfxy.sum()
        self.__img=tmp
        return meany

    def m2x(self):
        '''returns the second moment in x. In pixels'''
        tmp=self.__img
        xpixs=self.__img.shape[1] #number of x pixels (columns)
        ypixs=self.__img.shape[0] # number of y pixels (rows)
        self.normalize()
        matx=tile(arange(1,xpixs+1),(ypixs,1)) #make a matrix with all rows = (1,2, .. 780)
        x2fxy=self.__img*matx**2
        m2x=x2fxy.sum()
        self.__img=tmp
        return m2x

    def m2y(self):
        '''returns the second moment in y. In pixels'''
        tmp=self.__img
        xpixs=self.__img.shape[1] #number of x pixels (columns)
        ypixs=self.__img.shape[0] # number of y pixels (rows)
        self.normalize()
        maty=transpose(tile(arange(1,ypixs+1),(xpixs,1))) #make a matrix with all columns = (1,2, .. 780)
        y2fxy=self.__img*maty**2
        m2y=y2fxy.sum()
        self.__img=tmp
        return m2y

    def wx_d(self,in_pix=False):
        '''return the wx value calculated using the moments.'''
        w=2*sqrt(self.m2x()-self.mx()**2)
        if not in_pix: w=w*self.__cal
        return w

    def wy_d(self,in_pix=False):
        '''returns the wy value calculated using the moments.'''
        w=2*sqrt(self.m2y()-self.my()**2)
        if not in_pix: w=w*self.__cal
        return w

    def m(self):
        '''returns the means. In pixels'''
        return (self.mx(),self.my())

    
    def w_d(self,in_pix=False):
        '''returs the w values, using the moments.'''
        return (self.wx_d(in_pix=in_pix), self.wy_d(in_pix=in_pix))
    
    def cut(self,nw=3,size_in_pix=None):
        """ If size_in_pix=None : cut out everything but nw times the w of the beam.
            If size_in_pix=number: cut out square of size around the mean
        """
        tmp=self.__img
        self.bgsubtract(method='threshold')
        cx=self.mx()
        cy=self.my()
        if size_in_pix==None:
            dx=nw*self.wx_d(in_pix=True)
            dy=nw*self.wy_d(in_pix=True)
        else:
            dx=size_in_pix/2
            dy=size_in_pix/2
        self.__img=tmp[cy-dy:cy+dy,cx-dx:cx+dx]

    def lineout_x(self,plot_lineout=True):
        lo=sum(self.__img,axis=0)
        x=linspace(1,lo.size,lo.size)*self.__cal-self.mx()
        if plot_lineout:
            pyplot.plot(x,lo)
            pyplot.show()
        return (x,lo)
    
    def lineout_y(self,plot_lineout=True):
        lo=sum(self.__img,axis=1)
        y=linspace(1,lo.size,lo.size)*self.__cal-self.my()
        if plot_lineout:
            pyplot.plot(y,lo)
            pyplot.show()
        return (y,lo)

    def fit_lineout_x(self,plot_lineout=True):
        l1=self.lineout_x(plot_lineout=False)
        lsqfit=self.fit_gaus(l1,plot_fit=False)
        res=lsqfit[0]
        w=2*res[1]
        if plot_lineout:
            y=norm.pdf(l1[0],res[0],res[1])*res[2]*sqrt(2*pi*res[1]**2)+res[3]
            pyplot.plot(l1[0],y)
            pyplot.plot(l1[0],l1[1])
            pyplot.title('w = '+str(w))
            pyplot.show()
        return w

    def fit_lineout_y(self,plot_lineout=True):
        l1=self.lineout_y(plot_lineout=False)
        lsqfit=self.fit_gaus(l1,plot_fit=False)
        res=lsqfit[0]
        w=2*res[1]
        if plot_lineout:
            y=norm.pdf(l1[0],res[0],res[1])*res[2]*sqrt(2*pi*res[1]**2)+res[3]
            pyplot.plot(l1[0],y)
            pyplot.plot(l1[0],l1[1])
            pyplot.title('w = '+str(w))
            pyplot.show()
        return w
 


    def fit_gaus(self,lineout,plot_fit=True):
        """ fits with gaussian and plots, or return parameters.
    
            parameters returned: y= A exp((x-mu)^2/2*sigma^2)+offset
                            params: [mu,sigma,A,offset]
        """
        gaus=norm.pdf

        def objective(pars,y,x):
            mu=pars[0]
            sig=pars[1]
            hight=pars[2]
            offset=pars[3]
            err=y-hight*sqrt(2*pi)*sig*gaus(x,mu,sig)-offset
            return err
        ### initial guess before fit (based on moments)
        
        mu_i=(lineout[0]*lineout[1]).sum()/lineout[1].sum()
        sig_i=sqrt(((lineout[0]-mu_i)**2*lineout[1]).sum()/lineout[1].sum())
        hight_i=lineout[1].max()
        offset_i=0
        pars_i=[mu_i,sig_i,hight_i,offset_i]
        
        plsq=leastsq(objective,pars_i,args=(lineout[1],lineout[0]))
        if plot_fit:
            res=plsq[0]
            y=norm.pdf(lineout[0],res[0],res[1])*res[2]*sqrt(2*pi*res[1]**2)+res[3]
            pyplot.plot(lineout[0],y)
            pyplot.plot(lineout[0],lineout[1])
            pyplot.show()
        
        return plsq


    def w2fwhm(self,w):
        '''calculates fwhm when w is given'''
        return sqrt(2*log(2))*w

    def max(self):
        return self.__img.max()

    def grab(self,camera):
        ''' will grab an image from an mec camera. Needs to be implemented'''
        camimage=camera.grab(False)+0.0 #to make sure its a float, for later divisions
        self.imread(camimage)

    def grab_background(self,camera):
        '''grab an image from the camera and places it in .__bgimage. Overwrites the current background, if any.'''
        self.__bgimage=camera.grab(False)+0.0  #to make sure its a float, for later divisions

    def read_background(self,image):
        '''saves the images as the background. '''
        self.__bgimage=image+0.0  #to make sure it's a float

    def read_background_file(self,filename):
        '''read image from file, and saves in background'''
        self.__bgimage=image.imread(filename)+0.0 #to make sure its a float
    
    def save(self,filename=None):
        ''' pickles the object to file in filename.
            If filename=None, it saves to a standard name in the scandirectory of the
            experiment: config.scandata_directory
        '''
        if filename==None:
            timestr='_'+asctime()
            timestr=timestr.replace(" ","_")
            filename=self._save_dir+self.__name+timestr+'.pkl' 
         
        pickle.dump(self,open(filename,"wb"))

    def load(self,filename=None):
        '''loads a beam into the object. The filename needs to be a pickled (saved) beam.
           if no filename is give, a selector will pop up
        '''
        print("Sorry, in python you can't unpickle into self. To load a beam, type : ")
        print("In[#]: beamname = unpickle('filename')")
        print("You can leave the filename blank, and a popup will let you choose a file")
    
        
        


    ###########################################################################
    ###########################################################################
    ###########################################################################


class FocalScan(object):
    '''defines a focal scan, which is an array of images. It has functions that calculate and fit a focal scan.
    '''

    def __init__(self,name='focalscan'):
        self._stack=[]         # stack of images
        self._wx_d=([],[])     # list of wx vs. z based on moments
        self._wy_d=([],[])     # list of wy vs. z based on moments
        self._wx_lo=([],[])    # list of wx vs. z based on fits of LineOuts
        self._wy_lo=([],[])    # list of wy vs. z based of fits of LineOuts
        self._peak=([],[])     # plot of the maximum vs z. Depending on normalization this is flux, intensity or a.u.
        self.__landa=800e-9    # laser wavelength
        self.__bgimage=None    # background image. You can still have background images in each image of the stack
                               # but this makes the file pickled to disk rather large.
        self._save_dir=config.scandata_directory+'/' #standard directory to save stuff
        self._name=name

    def landa(self,l=None):
        if l==None: return self.__landa
        else: self.__landa=l

    def size(self):
        return len(self._stack)

    def add(self,newbeam):
        # if newbeam.__class__ != beam:
        #    print "Not a beam. Cannot add to focal scan" # check doesn't work. Not robust for now.
        self._stack.append(newbeam)

    def image(self,n):
        if n>self.size():print 'outside range'
        else: return self._stack[n-1]

    def view(self,image_number=None,in_pix=False):
        if image_number==None:
            for im in self._stack:im.show(in_pix=in_pix)               
        else: self._stack[image_number-1].show(in_pix=in_pix)


    

    def bgsubtract(self,refsquare=(1,20,1,20),bgimage=None,threshold=False,method='avg',image_number=None):
        print('Using method : '+method)
        if bgimage==None: bgimage=self.__bgimage
        if image_number==None:
            for im in self._stack:im.bgsubtract(refsquare=refsquare,bgimage=bgimage,threshold=threshold,method=method)
        else: self._stack[image_number].bgsubtract(refsquare=refsquare,bgimage=bgimage,threshold=threshold,method=method)

    def revert(self,image_number=None):
        '''revert all images in the scan, or the image number that is given'''
        if image_number==None:
            for im in self._stack:im.revert()
        else:self._stack[image_number].revert()
  


    def grab_bg(self,camera):
        '''grab an image from the camera and places it in .__bgimage. Overwrites the current background, if any.'''
        self.__bgimage=camera.grab(False)+0.0  #to make sure its a float, for later divisions

    def read_background(self,image):
        '''saves the images as the background. '''
        self.__bgimage=image+0.0  #to make sure it's a float

    def read_background_file(self,filename):
        '''read image from file, and saves in background'''
        self.__bgimage=image.imread(filename)+0.0 #to make sure its a float

    def read_background_beam(self,beam):
        ''' beam needs to be a beam object, the image of which will be used as background'''
        self.__bgimage=beam.export()+0.0 #to make sure its a float

    def show_bgimage(self):
        '''shows the bg image in the scan'''
        if self.__bgimage==None: print('no background image')
        else:
            pyplot.imshow(self.__bgimage)
            pyplot.title('Background Image')
            pyplot.colorbar()
            pyplot.show()

    def cut(self,image_number=None,nw=3,size_in_pix=None):
        '''cuts all images, or image number given, with 3 ws'''
        if image_number==None:
            for im in self._stack:im.cut(nw,size_in_pix=size_in_pix)
        else:self._stack[image_number].cut(nw,size_in_pix=size_in_pix)


    def flux(self,image_number=None):
        '''normalize to flux all images, or image number given, with 3 ws'''
        if image_number==None:
            for im in self._stack:im.flux()
        else:self._stack[image_number].flux()

    def intensity(self,image_number=None):
        '''normalize to intensity all images, or image number given, with 3 ws'''
        if image_number==None:
            for im in self._stack:im.intensity()
        else:self._stack[image_number].intensity()

    def sort(self):
        newstack=sorted(self._stack,key=lambda beam:beam.z())
        self._stack=newstack

    def normalize(self,image_number=None):
        '''normalizes all or given numbered image'''
        if image_number==None:
            for im in self._stack:im.normalize()
        else:self._stack[image_number].normalize()

    def calc_wx_d(self,clear=True,in_pix=False):
        if clear:self.clear_wx_d()
        for im in self._stack:
            self._wx_d[0].append(im.z())
            self._wx_d[1].append(im.wx_d(in_pix=in_pix))

    def show_wx_d(self,plot_fit=True):
        pyplot.plot(self._wx_d[0],self._wx_d[1])
        if plot_fit:
            params=self.fit_w(self._wx_d,plot_fit=False)
            res=params[0]
            w0=res[0]
            z0=res[1]
            M2=res[2]
            z_min=min(self._wx_d[0])
            z_max=max(self._wx_d[0])
            z=linspace(z_min,z_max,100)
            w=w0*sqrt(1+(M2*(z-z0)*self.__landa/(pi*w0**2))**2)
            pyplot.plot(z,w)
            pyplot.title('wx0 = '+str(w0)+' , zx0 = '+str(z0)+' , Mx2 = '+str(M2))
        pyplot.show()

    def calc_wy_d(self,clear=True,in_pix=False):
        if clear:self.clear_wy_d()
        for im in self._stack:
            self._wy_d[0].append(im.z())
            self._wy_d[1].append(im.wy_d(in_pix=in_pix))

    def calc_w_d(self,clear=True,in_pix=False):
        self.calc_wx_d(clear=clear,in_pix=in_pix)
        self.calc_wy_d(clear=clear,in_pix=in_pix)

    def show_wy_d(self,plot_fit=True):
        pyplot.plot(self._wy_d[0],self._wy_d[1])
        if plot_fit:
            params=self.fit_w(self._wy_d,plot_fit=False)
            res=params[0]
            w0=res[0]
            z0=res[1]
            M2=res[2]
            z_min=min(self._wy_d[0])
            z_max=max(self._wy_d[0])
            z=linspace(z_min,z_max,100)
            w=w0*sqrt(1+(M2*(z-z0)*self.__landa/(pi*w0**2))**2)
            pyplot.plot(z,w)
            pyplot.title('wy0 = '+str(w0)+' , zy0 = '+str(z0)+' , My2 = '+str(M2))
        pyplot.show()
        
    def get_wx_d(self):
        return self._wx_d

    def get_wy_d(self):
        return self._wy_d

    def show_w_d(self,plot_fit=True):
         pyplot.plot(self._wx_d[0],self._wx_d[1])
         pyplot.plot(self._wy_d[0],self._wy_d[1])
         if plot_fit:
            params=self.fit_w(self._wx_d,plot_fit=False)
            res=params[0]
            w0=res[0]
            z0=res[1]
            M2=res[2]
            z_min=min(self._wx_d[0])
            z_max=max(self._wx_d[0])
            z=linspace(z_min,z_max,100)
            w=w0*sqrt(1+(M2*(z-z0)*self.__landa/(pi*w0**2))**2)
            pyplot.plot(z,w)
            titlestr='wx0 = '+str(w0)+' , zx0 = '+str(z0)+' , Mx2 = '+str(M2)
            params=self.fit_w(self._wy_d,plot_fit=False)
            res=params[0]
            w0=res[0]
            z0=res[1]
            M2=res[2]
            z_min=min(self._wy_d[0])
            z_max=max(self._wy_d[0])
            z=linspace(z_min,z_max,100)
            w=w0*sqrt(1+(M2*(z-z0)*self.__landa/(pi*w0**2))**2)
            pyplot.plot(z,w)
            titlestr+='\nwy0 = '+str(w0)+' , zy0 = '+str(z0)+' , My2 = '+str(M2)
            pyplot.title(titlestr)
         
         pyplot.show()

    def clear_stack(self):
        self._stack=[]

    def clear_wx_d(self):
        self._wx_d=([],[])

    def clear_wy_d(self):
        self._wy_d=([],[])

    def clear_peak(self):
        self._peak=([],[])

    def clear_wx_lo(self):
        self._wx_lo=([],[])

    def clear_wy_lo(self):
        self._wy_lo=([],[])

    def clear_all(self):
        self.clear_stack()
        self.clear_wx_d()
        self.clear_wy_d()
        self.clear_wx_lo()
        self.clear_wy_lo()
        
    def calc_wx_lo(self,clear=True):
        if clear:self.clear_wx_lo()
        for im in self._stack:
            self._wx_lo[0].append(im.z())
            self._wx_lo[1].append(im.fit_lineout_x(False))

    def calc_peak(self,clear=True):
        if clear:self.clear_peak()
        for im in self._stack:
            self._peak[0].append(im.z())
            self._peak[1].append(im.max())

    def calc_wy_lo(self,clear=True):
        if clear:self.clear_wy_lo()
        for im in self._stack:
            self._wy_lo[0].append(im.z())
            self._wy_lo[1].append(im.fit_lineout_y(False))

    def calc_w_lo(self,clear=True):
        self.calc_wx_lo(clear=clear)
        self.calc_wy_lo(clear=clear)

    def show_wy_lo(self,plot_fit=True):
        pyplot.plot(self._wy_lo[0],self._wy_lo[1])
        if plot_fit:
            params=self.fit_w(self._wy_lo,plot_fit=False)
            res=params[0]
            w0=res[0]
            z0=res[1]
            M2=res[2]
            z_min=min(self._wy_lo[0])
            z_max=max(self._wy_lo[0])
            z=linspace(z_min,z_max,100)
            w=w0*sqrt(1+(M2*(z-z0)*self.__landa/(pi*w0**2))**2)
            pyplot.plot(z,w)
            pyplot.title('wy0 = '+str(w0)+' , zy0 = '+str(z0)+' , My2 = '+str(M2))
        pyplot.show()

    def show_wx_lo(self,plot_fit=True):
        pyplot.plot(self._wx_lo[0],self._wx_lo[1])
        if plot_fit:
            params=self.fit_w(self._wx_lo,plot_fit=False)
            res=params[0]
            w0=res[0]
            z0=res[1]
            M2=res[2]
            z_min=min(self._wx_lo[0])
            z_max=max(self._wx_lo[0])
            z=linspace(z_min,z_max,100)
            w=w0*sqrt(1+(M2*(z-z0)*self.__landa/(pi*w0**2))**2)
            pyplot.plot(z,w)
            pyplot.title('wx0 = '+str(w0)+' , zx0 = '+str(z0)+' , Mx2 = '+str(M2))
        pyplot.show()

    def show_w_lo(self,plot_fit=True):
         pyplot.plot(self._wx_lo[0],self._wx_lo[1])
         pyplot.plot(self._wy_lo[0],self._wy_lo[1])
         if plot_fit:
            params=self.fit_w(self._wx_lo,plot_fit=False)
            res=params[0]
            w0=res[0]
            z0=res[1]
            M2=res[2]
            z_min=min(self._wx_lo[0])
            z_max=max(self._wx_lo[0])
            z=linspace(z_min,z_max,100)
            w=w0*sqrt(1+(M2*(z-z0)*self.__landa/(pi*w0**2))**2)
            pyplot.plot(z,w)
            titlestr='wx0 = '+str(w0)+' , zx0 = '+str(z0)+' , Mx2 = '+str(M2)
            params=self.fit_w(self._wy_lo,plot_fit=False)
            res=params[0]
            w0=res[0]
            z0=res[1]
            M2=res[2]
            z_min=min(self._wy_lo[0])
            z_max=max(self._wy_lo[0])
            z=linspace(z_min,z_max,100)
            w=w0*sqrt(1+(M2*(z-z0)*self.__landa/(pi*w0**2))**2)
            pyplot.plot(z,w)
            titlestr+='\nwy0 = '+str(w0)+' , zy0 = '+str(z0)+' , My2 = '+str(M2)
            pyplot.title(titlestr)
        
         pyplot.show()

    def show_peak(self):
        pyplot.plot(self._peak[0],self._peak[1])
        pyplot.show()

        
    def get_wx_lo(self):
        return self._wx_lo

    def get_wy_lo(self):
        return self._wy_lo

    def cal(self,newcal=None):
        if newcal==None:
            for im in self._stack:print im.cal(m_per_pix=newcal)
        else:
            for im in self._stack:im.cal(m_per_pix=newcal)

    def energy(self,en=None):
        '''puts energy in all images'''
        if en==None:
            for im in self._stack:print im.energy(en=en)
        else:
            for im in self._stack:im.energy(en=en)

    def pulse_length(self,pl=None):
        '''puts pulse length in all images'''
        if pl==None:
            for im in self._stack:print im.pulse_length(pl=pl)
        else:
            for im in self._stack:im.pulse_length(pl=pl)


    def fit_w(self,wlist,plot_fit=True):
        '''fits the wlist for w0, M2 and z0'''
        landa=self.landa()
        

        def objective(pars,w,z):
           w0=pars[0]
           z0=pars[1]
           M2=pars[2]
           err=w-w0*sqrt(1+(M2*(z-z0)*landa/(pi*w0**2))**2)
           return err

        ### initial guess, based on perfect beam and min of wlist
        w0_i=min(wlist[1])
        z0_i=wlist[0][wlist[1].index(min(wlist[1]))]
        M2_i=1
        pars_i=[w0_i,z0_i,M2_i]

        wl_lsq=leastsq(objective,pars_i,args=(wlist[1],wlist[0]))

        if plot_fit:
            res=wl_lsq[0]
            w0=res[0]
            z0=res[1]
            M2=res[2]
            z_min=min(wlist[0])
            z_max=max(wlist[0])
            z=linspace(z_min,z_max,100)
            w=w0*sqrt(1+(M2*(z-z0)*landa/(pi*w0**2))**2)
            pyplot.plot(z,w)
            pyplot.plot(wlist[0],wlist[1])
            pyplot.title('w0 = '+str(w0)+' ,z0 = '+str(z0)+' , M2 = '+str(M2))
            pyplot.show()
        return wl_lsq


    def save(self,filename=None):
        ''' pickles the object to file in filename.
            If filename=None, it saves to a standard name in the scandirectory of the
            experiment: config.scandata_directory
        '''
        if filename==None:
            timestr='_'+asctime()
            timestr=timestr.replace(" ","_")
            filename=self._save_dir+self._name+timestr+'.pkl' 
         
        pickle.dump(self,open(filename,"wb"))

    def load(self,filename=None):
        '''Gives loading instructions.
        '''
        print("Sorry, in python you can't unpickle into self. To load a focalscan, type : ")
        print("In[#]: focalscanname = unpickle('filename')")
        print("You can leave the filename blank, and a popup will let you choose a file")


    def grab(self,camera,name=None,cal=None,pulselength=None,energy=None,landa=800e-9,z=None): 
        ''' grabs image from camera, and adds to the focal scan.
            useage: grab(self,camera,name=None,cal=None,pulselength=None,energy=None,landa=800e-9,z=None): 
           Still needs to be implemented
        '''
        badd=Beam()
        badd.grab(camera)
        if name!=None:         badd.name(name)
        if cal!=None:          badd.cal(cal+0.0)
        if pulselength!=None: badd.pulse_length(pulselength+0.0)
        if energy!=None:       badd.energy(energy+0.0)
        badd.landa(landa)
        if z!=None:            badd.z(z+0.0)

        self.add(badd)
        
    def show_z(self,zpos):
        '''shows the images closest to the z-position given'''
        index=0
        z_closest=self.image(0).z()
        index_closest=0
        for beam in self._stack:
            if abs(zpos-beam.z())<abs(zpos-z_closest):
                z_closest=beam.z()
                index_closest=index
            index+=1
        self.view(index_closest)
        

    def recordscan(self,motor,range,camera,images_per_z=1,name=None,cal=None,pulselength=None,energy=None,landa=800e-9,new=False): 
        '''records a full focal scan with motor and camera.range=(begin,end,#steps).
           range is in the motor units, which is assumed to be mm. So this is multiplied by e-3 and put in the z register.
           useage:recordscan(self,motor,range,camera,name=None,cal=None,pulselength=None,energy=None,landa=800e-9,new=False): 
           It adds the images, unless new=True, in which case the scan is first cleared
        '''
        zpositions=linspace(range[0],range[1],range[2])

        for zpos in zpositions:
            motor.umv(zpos)
            for index in arange(images_per_z):
              self.grab(camera,z=zpos*1e-3,cal=cal,pulselength=pulselength,energy=energy,landa=landa)
              time.sleep(0.1)
        
    def recordscan_autogain(self,motor,range,camera,images_per_z=1,name=None,cal=None,pulselength=None,energy=None,landa=800e-9,new=False,FilterChange=True): 
        '''records a full focal scan with motor and camera.range=(begin,end,#steps).
           range is in the motor units, which is assumed to be mm. So this is multiplied by e-3 and put in the z register.
           useage:recordscan(self,motor,range,camera,name=None,cal=None,pulselength=None,energy=None,landa=800e-9,new=False): 
           It adds the images, unless new=True, in which case the scan is first cleared
           The camera takes a first images, which is used to set the gain such that the maximum count is around 200counts.
           If FilterChange=True, and the gain needed for this is out of range (either below 0 or above 32), the user is prompted
           to place a ND or take one away.
        '''
        print("AUTOGAIN FUNCTION NOT IMPLEMENTED YET")
        gain_high_lim=32
        gain_low_lim=0
        count_goal=210.0  # the number of counts we want in the maximum. Should be close but below 256. 210 seem safe.
        zpositions=linspace(range[0],range[1],range[2])
        k=KeyPress.KeyPress()
        no_filte_change=not(FilterChange)
        for zpos in zpositions:
            motor.umv(zpos)
            ### Set gain correctly: we want 210counts in the maximum.
            wait_for_gain=True
            while wait_for_gain :
                factor=count_goal/camera.grab().max()
                current_gain=camera.gain()
                new_gain=current_gain+20.0*log10(factor)
                if (gain_low_lim <= new_gain <= gain_high_lim) or no_filter_change:
                    wait_for_gain=False
                    camera.gain(new_gain)
                elif new_gain<gain_low_lim:
                    print("Camera saturated. Add OD~1. Press any key when done or 'c' to continue without further warnings.")
                    k.waitkey()
                    if k.iskey("c"): no_filter_change=True
                elif new_gain>gain_high_lim:
                    print("Camera counts low. Remove OD~1. Press any key when done or 'c' to continue without further warnings.")
                    k.waitkey()
                    if k.iskey("c"): no_filter_change=True
                    
            time.sleep(0.01)
            
            for index in arange(images_per_z):
              self.grab(camera,z=zpos*1e-3,cal=cal,pulselength=pulselength,energy=energy,landa=landa)
              time.sleep(0.1)

    
        
    
