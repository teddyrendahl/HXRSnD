from pylab import *
from kulletools import *
#from recspaccalc import *
import numpy


class crystal(object):
  def __init__(self,uc={'a':2*pi,'b':2*pi,'c':2*pi,'alpha':90,'beta':90,'gamma':90},crystalRotMat=matrix(eye(3))):
    """Unit cell angles in degrees"""
    if type(uc)==dict:
      self.uc = dict2class(uc)
    elif type(uc)==tuple:
      self.uc = slef._get_uc_from_tuple(uc)
    else:
      self.uc = uc
    self.crystalRotMat = crystalRotMat

  def ucvectors(self):
    uc = self.uc
    av = array([uc.a,0,0])
    bv = array([uc.b*cos(deg2rad(uc.gamma)),uc.b*sin(deg2rad(uc.gamma)),0])
    cx = uc.c*cos(deg2rad(uc.beta))          
    cy = 1./sin(deg2rad(uc.gamma))*(uc.c*cos(deg2rad(uc.alpha))-cx*cos(deg2rad(uc.gamma)))
    cz = sqrt(uc.c**2-cx**2-cy**2)
    cv = array([cx, cy, cz]);
    R = self.crystalRotMat
    av = matrix(R)*matrix(av).ravel().transpose()
    bv = matrix(R)*matrix(bv).ravel().transpose()
    cv = matrix(R)*matrix(cv).ravel().transpose()
    return asarray(av.transpose()),asarray(bv.transpose()),asarray(cv.transpose())

  def reclattvectors(self):
    av,bv,cv = self.ucvectors()
    av=av.ravel();bv=bv.ravel();cv=cv.ravel();
    Vc=dot(av, cross(bv,cv));
    avr=2*pi/Vc*cross(bv, cv);
    bvr=2*pi/Vc*cross(cv, av);
    cvr=2*pi/Vc*cross(av, bv);
    return avr,bvr,cvr

  def getQhkl(self,hkl):
    avr,bvr,cvr = self.reclattvectors()
    Q = hkl[0]*avr+hkl[1]*bvr+hkl[2]*cvr
    return Q

  def rotate_vec_parralel_to_rotax(self,vec):
    self.crystalRotMat = rotmat3Dfrom2vectors(vec,array([0,0,1]))
    
  def rotate_around_rotax_to_get_vecs_in_plane(self,v0,v1):
    v0 = cross(array([0,0,1]),v0)
    v1 = cross(array([0,0,1]),v1)
    print rotmat3Dfrom2vectors(v0,v1)
    self.crystalRotMat = rotmat3Dfrom2vectors(v0,v1)*self.crystalRotMat
    
  def _get_uc_from_tuple(self,uc):
    uc_dict = dict(a=uc[0],b=uc[1],c=uc[2],alpha=uc[3],beta=uc[4],gamma=uc[5])
    uc_class = dict2class(uc_dict)
    return uc_class

  def _isallowed(self,hkl):
    if self.packing is 'fcc':
      if not isodd(sum(hkl)):
        isallowed = True
      else:
        isallowed = False
    if self.packing is 'bcc':
      if isodd(hkl[0])==isodd(hkl[1])==isodd(hkl[2]):
        isallowed = True
      else:
        isallowed = False
    if self.packing is 'diamond':
      if (isodd(hkl[0])==isodd(hkl[1])==isodd(hkl[2])) or (sum(hkl)/4.).is_integer():
        isallowed = True
      else:
        isallowed = False
    if self.packing is 'cubic':
        isallowed = True
    else:
      print "crystal structure not implemented (yet)"

  #def setCrystalRotationFromEtaRotationAxis(self):
    #"""Calculates the rotation matrix to get from the standard ctystal rotation (normal axis to uc ab plane) to the phiRotationAxis"""
    #rotnormal = cross(array([0,0,1]),self.etaRotationAxis)
    #rotnormal = rotnormal/numpy.linalg.norm(rotnormal)
    #rotangle = arccos(dot(array([0,0,1]),self.etaRotationAxis))
    #self.crystR0 = rotmat3D(rotnormal,rotangle)
  #def getRotMatFromRealHkl(self,hkl):
  #def getRotMatFromReciprocalHkl(self,hkl):




class xray(object):
  def __init__ (self,Ephot=lam2E(1),XrayDirection=[1,0,0],phiRotationAxis=[0,0,1],etaRotationAxis=[0,-1,0]):
    """crystal coordinate system. The diffractometer rotation phi is assumed in crystal frame z-direction"""
    self.Ephot = Ephot
    self.Lambda = E2lam(self.Ephot)
    self.phiRotationAxis = array(phiRotationAxis)
    self.etaRotationAxis = array(etaRotationAxis)
    self.XrayDirection = array(XrayDirection)
    self.K = 2*pi/self.Lambda
    self.Kvec = self.getKvec()
    self.setIncidenceAngle()

  def getKvec(self):
    k = 2*pi/E2lam(self.Ephot)*self.XrayDirection
    return k

  def setIncidenceAngle(self,eta=0):
    self.etaRotationAxis = rotmat3D([0,1,0],-eta)*matrix(self.etaRotationAxis).ravel().transpose()
    self.etaRotationAxis = array(self.etaRotationAxis).ravel()
    self.eta = pi/2 - arccos(dot(self.etaRotationAxis,self.XrayDirection))

  #def getIncidenceAngle(self,eta):
    #"""get """
    #self.etaRotationAxis = rotmat3D([0,1,0],-eta)*matrix(self.etaRotationAxis).ravel().transpose()
    #self.etaRotationAxis = array(self.etaRotationAxis).ravel()
    #self.eta = pi/2 - arccos(dot(self.etaRotationAxis,self.XrayDirection))

  def setRotationAxis(self,v):
    self.RotationAxis = v/numpy.linalg.norm(v)

  def setXrayDirection(self,v):
    self.XrayDirection = v/numpy.linalg.norm(v)

  def getPhiRotationhkl(self,crystal,hkl):
    Q = crystal.getQhkl(hkl)
    #Q = self.crystR0*matrix(Q).ravel().transpose()
    Q = array(Q.ravel())
    phi,phiE = self.getPhiRotation(Q)
    return phi,phiE
  def getQpQn(self,Q):
    Qnorm = self.getQnorm(Q)
    Qn = dot(Q,self.phiRotationAxis)
    Qp = sqrt(Qnorm**2-Qn**2)
    return Qp,Qn
  def getQnorm(self,Q):
    Qnorm = numpy.linalg.norm(Q)
    return Qnorm

  def getPhiRotation(self,Q):
    Qnorm = self.getQnorm(Q)
    Qp,Qn = self.getQpQn(Q)
    #Qnorm = numpy.linalg.norm(Q)
    #Qn = dot(Q,self.phiRotationAxis)
    #Qp = sqrt(Qnorm**2-Qn**2)
    nv = cross(self.phiRotationAxis,Q)
    nv = nv/numpy.linalg.norm(nv)
    phi = arccos(dot([1,0,0],list(nv.ravel())))-pi/2
    #phi = asin(-G.^2./Gr0.*lambda./4./pi.*sec(eta) + Gz0./Gr0.*tan(eta));
    phiE = arcsin(Qnorm**2/(2*self.K*Qp*cos(self.eta))+Qn/Qp*tan(self.eta))
    return phi,phiE

  def getDiffrationAnglesHkl(self,C,hkl):
    Q = C.getQhkl(hkl)
    phi,phiE = self.getPhiRotation(Q)
    Q = rotmat3D(self.phiRotationAxis,phi+phiE)*matrix(Q).ravel().transpose()
    Q = rotmat3D(self.etaRotationAxis,self.eta)*matrix(Q).ravel().transpose()
    kout = self.Kvec+asarray(Q).ravel().transpose()
    el = arcsin(kout[2]/self.K)
    az = arctan(kout[1]/kout[0])
    return az,el
    



      

def E2lam(E):
  lam = 12.39842 /E
  return lam

def lam2E(lam):
  E = 12.39842 / lam;  #/keV
  return E


#def get_unit_cell(name):

def revertElAz(el,az):
  elO=arcsin(cos(el)*sin(az))
  azO=-arctan(sin(el)/(cos(el)*cos(az)))
  return elO,azO


  
