from kulletools import *
from numpy import *
import scipy as s
from pylab import *
import types
#import minuit

def nfigure(name="noname"):
	from pylab import figure
	import matplotlib
	try:
		fig_names = [x.canvas.manager.window.get_title()
				for x in matplotlib._pylab_helpers.Gcf.get_all_fig_managers()]
	except:
		fig_names = [x.canvas.manager.window.wm_title()
				for x in matplotlib._pylab_helpers.Gcf.get_all_fig_managers()]
	#import code; code.interact(local=locals())

	n=0
	found=0
	for tname in fig_names:
		n+=1
		if tname == name:
			fig=matplotlib._pylab_helpers.Gcf.get_all_fig_managers()[n-1]
			matplotlib._pylab_helpers.Gcf.set_active(fig)
			fig = gcf()
			found = 1
			
	if not found==1:
		print 'Created new figure %s'  % (name)
		fig = figure()
		fig.canvas.set_window_title(name)
#	figure(fig.number)
	return fig

def draw_verticalline(pos=0,linespec='k'):
  ah = gca()
  yl = ah.get_ylim()
  plot(pos*ones(2),yl,linespec)

def draw_horizontalline(pos=0,linespec='k'):
  ah = gca()
  xl = ah.get_xlim()
  plot(xl,pos*ones(2),linespec)

def eV2reccm(eV):
	reccm =  eV* 8065.54445
	return reccm

def reccm2eV(reccm):
	eV = reccm / 8065.54445
	return eV

def eV2nm(eVvec):
	nmvec = 1e9*h_planck()* c_light() / eV2J(eVvec)
	return nmvec

def nm2eV(nmvec):
	eVvec = J2eV(1e9*h_planck()*c_light()/nmvec)
	return eVvec

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
  """3D rotation matrix around axis v about angle ang"""
  ux = v[0]
  uy = v[1]
  uz = v[2]
  c = cos(ang)
  s = sin(ang)
  rotmat = matrix(
  [[ux**2+(1-ux**2)*c , ux*uy*(1-c)-uz*s , ux*uz*(1-c)+uy*s],
  [ux*uy*(1-c)+uz*s , uy**2+(1-uy**2)*c , uy*uz*(1-c)-ux*s],
  [ux*uz*(1-c)-uy*s , uy*uz*(1-c)+ux*s , uz**2+(1-uz**2)*c]]);
  rotmat = matrix(rotmat)
  return rotmat
def rotmat3Dfrom2vectors(v0,v1):
  """calculate 3D rotation matrix that rotates from v0 to v1"""
  v0 = v0/norm(v0)
  v1 = v1/norm(v1)
  ax = cross(v0,v1);
  ang = arcsin(norm(ax))
  ax = ax/norm(ax)
  rotmat = rotmat3D(ax,ang)
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

def digitize2D(x1,x2,bins1,bins2):
	bn1 = digitize(x1,bins1)
	bn2 = digitize(x2,bins2)
	sz1 = bins1.shape[0]+1
	sz2 = bins2.shape[0]+1
	bnmat = reshape(arange(sz1*sz2),[sz1,sz2])
	bn = bnmat[bn1,bn2]
	return bn

def MAD(a, c=0.6745, axis=0):
	"""
	Median Absolute Deviation along given axis of an array:
	median(abs(a - median(a))) / c
	"""
	a = N.asarray(a, N.float64)
	d = median(a, axis=axis)
	d = unsqueeze(d, axis, a.shape)
	return median(N.fabs(a - d) / c, axis=axis)

#def minuitfit(function,startpars,xdat,ydat,edat=None,fixedpar=None,stepszpar=None,limitspar=None):
	#"""
	#Wrapper function for minuit to do Chi squared based fits on 
	#simple function of format:
	#ydat_calculated = function(dict(par1=...,par2=...,...) , xdat)
	#Other minuit parameters like the initial stepsize, parameter 
	#fixing and limits (not implemented yet) can be given as both
	#dictionary and list.
	#"""
	#if edat is None:
		#edat = ones(shape(ydat))
	#elif shape(edat)==(1,):
		#edat = edat*ones(shape(ydat))

	## internal global variables
	#g = globals()
	#g['idat'] = xdat
	#g['odat'] = ydat
	#g['edat'] = edat
	#g['function'] = function

	## make dict from parameters is necessary and get most 
	## important strings for the minuit variable workaround
	#pardef = function.func_defaults[0]
	#varstr = ''
	#varstrstartval = ''
	#varstrval = ''
	#if startpars is not dict:
		#splist = startpars
		#startpars = dict()
		#for tpar in pardef.keys():
			#startpars[tpar] = splist[pardef.keys().index(tpar)]

	#for tpar in pardef.keys():
		#varstrstartval += '%s=startpars[\'%s\'],'%(tpar,tpar)
		#varstrval += '%s=%s,'%(tpar,tpar)
		#varstr += '%s,'%(tpar)
	#varstr = varstr[:-1]
	#varstrval = varstrval[:-1]
	#varstrstartval = varstrstartval[:-1]



	## make fixed string
	#if fixedpar is not None:
		#if type(fixedpar) is dict:
			#fixlist = []
			#for tpar in pardef.keys():
				#if tpar in fixedpar.keys():
					#fixlist.append(fixedpar[tpar])
				#else:
					#fixlist.append(False)
		#elif type(fixedpar) is list:
			#fixlist = fixedpar
		#fixstr = ''
		#for tpar in pardef.keys():
			#fixstr += 'fix_%s=%s,'%(tpar,fixlist[pardef.keys().index(tpar)])

		#fixstr = fixstr[:-1]
	## make stepsize string
	#if stepszpar is not None:
		#if type(stepszpar) is dict:
			#stepszlist = []
			#for tpar in pardef.keys():
				#if tpar in stepszpar.keys():
					#stepszlist.append(stepszpar[tpar])
				#else:
					#fixlist.append(None)
		#elif type(stepszpar) is list:
			#stepszlist = stepszpar
		#stepszstr = ''
		#for tpar in pardef.keys():
			#if stepszlist[pardef.keys().index(tpar)] is not None:
				#stepszstr += 'err_%s=%s,'%(tpar,stepszlist[pardef.keys().index(tpar)])

		#stepszstr = stepszstr[:-1]
	## make chisq function
	#csstr  = 'def chisq('+varstr+'): cs = sum(((odat-function(dict('+varstrval+'),idat))/edat)**2); return cs'
	#exec(csstr)
	#mstr = 'minuit.Minuit(chisq,'+varstrstartval
	#if stepszpar is not None:
		#mstr += stepszstr
	#if fixedpar is not None:
		#mstr += fixstr
	#mstr += ')'
	#m = eval(mstr)
	#return m
def isodd(num):
  return num & 1 and True or False

################# BASIC FIT FUNCTIONS ####################
def gauss(par=dict(A=[],pos=[],sig=[]),dat=[]):
	res = par['A']*exp(-(dat-par['pos'])**2/par['sig']**2/2)
	return res

