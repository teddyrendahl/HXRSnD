"""
Henriks collection of tools for plotting, frequent calculations etc.
"""
from tools import *
from numpy import *
import scipy as s
from pylab import *
import types

def nfigure(name):
	from pylab import figure
	import matplotlib
	try:
		fig_names = [x.canvas.manager.window.get_title()
				for x in matplotlib._pylab_helpers.Gcf.get_all_fig_managers()]
	except:
		fig_names = [x.canvas.manager.window.wm_title()
				for x in matplotlib._pylab_helpers.Gcf.get_all_fig_managers()]

	n=0
	found=0
	for tname in fig_names:
		n+=1
		if tname == name:
			fig=matplotlib._pylab_helpers.Gcf.get_all_fig_managers()[n-1]
			matplotlib._pylab_helpers.Gcf.set_active(fig)
			found = 1
			
	if not found==1:
		print 'Created new figure %s'  % (name)
		fig = figure()
		fig.canvas.set_window_title(name)
#	figure(fig.number)
	return fig

def eV2reccm(eV):
	reccm =  eV* 8065.54445
	return reccm

def reccm2eV(reccm):
	eV = reccm / 8065.54445
	return eV

def eV2nm(eVvec):
	nmvec = 1e9*h_planck()* c_light() / eV2J(eVvec)
	return nmvec

def eV2J(eV):
	J = 1.60217646e-19 * eV
	return J

def J2eV(J):
	eV = J/1.60217646e-19
	return eV

def c_light():
	c = 299792458 # m/s
	return c

def h_planck():
	h = 6.626068e-34 # m2 kg / s
	return h

def E2lam(E):
	lam = 12.39842 /E
	return lam

def lam2E(lam):
	E = 12.39842 / lam;  #/keV
	return E

def filtvec(vec,lims):
	filtbool = vec>min(lims) & vec<max(lims);
	return filtbool
def rotmat3D(v,ang):
	ux = v[0]
	uy = v[1]
	uz = v[2]
	c = cos(ang)
	s = sin(ang)
	rotmat = array(
	[[ux**2+(1-ux**2)*c , ux*uy*(1-c)-uz*s , ux*uz*(1-c)+uy*s],
	[ux*uy*(1-c)+uz*s , uy**2+(1-uy**2)*c , uy*uz*(1-c)-ux*s],
	[ux*uz*(1-c)-uy*s , uy*uz*(1-c)+ux*s , uz**2+(1-uz**2)*c]]);
	return rotmat

def poiss_prob(x,count):
	x = array(x)
	P = zeros(x.shape)
	i=0
	for xx in x:
		P[i] = count**xx *exp(-count)/s.factorial(xx)
		i=i+1
	return P
def gauss_amp(X,xdat):
	ydat = X[0]*exp(-(xdat-X[1])**2/2/X[2]**2)
	return ydat

def gauss_norm(X,xdat):
	ydat = 1./sqrt(2.*pi*X[2]**2)*X[0]*exp(-(xdat-X[1])**2/2/X[2]**2)
	return ydat

def chisqwrap(X,fun,xdat,ydat,bg_order=[]):
	"""
	Usage e.g. with scipy.optimize.fmin:
	fmin(chisqwrap,[1,1,1,0,0],args = (gauss_amp,x,y,1))
	"""
	ycalc = fun(X[0:shape(xdat)[0]-(bg_order)-1],xdat)+polyval(X[shape(xdat)[0]-(bg_order)-1:],xdat)
	chisq = sum((ydat-ycalc)**2)
	return chisq

def get_nargout():
    """Return how many values the caller is expecting."""
    import inspect, dis
    f = inspect.currentframe()
    f = f.f_back.f_back
    c = f.f_code
    i = f.f_lasti
    bytecode = c.co_code
    instruction = ord(bytecode[i+3])
    if instruction == dis.opmap['UNPACK_SEQUENCE']:
        howmany = ord(bytecode[i+4])
        return howmany
    elif instruction == dis.opmap['POP_TOP']:
        return 0
    return 1

def _get_argout_name():
    """Return name of variable that return value will be assigned to."""
    import inspect, dis
    f = inspect.currentframe()
    f = f.f_back.f_back
    c = f.f_code
    # dis.disassemble_string(c.co_code)
    i = f.f_lasti
    bytecode = c.co_code
    instruction = ord(bytecode[i+3])
    if instruction != dis.opmap['STORE_NAME']:
        # POP_TOP, ROT_TWO and UNPACK_SEQUENCE are not allowed in MATLAB
        # fro constructors
        error("Construction assignment into multiple values is not allowed.")
    name = c.co_names[ord(bytecode[i+4])]
    return name

def filtvec(v,lims):
	return logical_and(v>min(lims),v<max(lims))

def oversample(v,fac):
	vo = linspace(min(v),max(v),v.shape[0]*fac)
	return vo

def pol2cart(theta, radius, units='deg'):
    """Convert from polar to cartesian coordinates 
     
    **usage**: 
        x,y = pol2cart(theta, radius, units='deg') 
    """
    if units in ['deg', 'degs']:
        theta = theta*pi/180.0
    xx = radius*cos(theta)
    yy = radius*sin(theta)

    return xx,yy
#---------------------------------------------------------------------- 
def  cart2pol(x,y, units='deg'):
    """Convert from cartesian to polar coordinates 
     
    **usage**: 
        theta, radius = pol2cart(x, y, units='deg') 
         
    units refers to the units (rad or deg) for theta that should be returned"""
    radius= hypot(x,y)
    theta= arctan2(y,x)
    if units in ['deg', 'degs']:
        theta=theta*180/pi
    return theta, radius

def dict2class(d):
    """Return a class that has same attributes/values and 
       dictionaries key/value
    """
    
    #see if it is indeed a dictionary
    if type(d) != types.DictType:
        return None
    
    #define a dummy class
    class Dummy:
        pass
        
    c = Dummy
    for elem in d.keys():
        c.__dict__[elem] = d[elem]
    return c
#def interactiveInput(func,blabla,):
  #pass
 # 

#def funcToMethod(func, clas, method_name=None):
#   setattr(clas, method_name or func.__name__, func)
#
#class transplant:
#   def __init__(self, method, host, method_name=None):
#      self.host = host
#      self.method = method
#      setattr(host, method_name or method.__name__, self)
#
#   def __call__(self, *args, **kwargs):
#      nargs = [self.host]
#      nargs.extend(args)
#      return apply(self.method, nargs, kwargs)
