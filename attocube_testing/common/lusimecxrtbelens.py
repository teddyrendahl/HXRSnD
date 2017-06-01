#!/usr/bin/python
# This module provides support 
# for operations of the MEC XRT Beryllium focusing lens
# Author:         Zhou Xing (SLAC)
# Created:        Jan, 2015


from common import linac
from common.utilitiesBeLenses import calcFocalLength 
from scipy.interpolate import interp1d
import numpy as np
import math

lcls_linac=linac.Linac()

class XRTBeLens:
    """ Class that controls the XRT Be refractive focusing system for MEC"""
    def __init__(self,desc="MEC XRT Be Lens System"):
        # tabulated dispersive decrement
        self.delta = {1000.:0.000352431, 2000.:0.0000862, 3000.:0.0000381, 4000.:0.0000214, 5000.:0.0000137, 6000.:9.48e-6,\
                                    7000.:6.96e-6,8000.:5.33e-6,9000.:4.21e-6,10000.:3.41e-6}
        # tabulated mass attenuation
        self.beta = {1000.:0.0000109, 2000.:6.8e-7,3000.:1.29e-7,4000.:3.92e-8,5000.:1.56e-8,6000.:7.35e-9,7000.:3.94e-9, \
                     8000:2.34e-9,9000.:1.5e-9,10000.:1.03e-9}
        # ev to Angstrom constant
        self.lambdaToE = 12398. # E(ev) * lambda(A) = 12398
        # thickness of lens, approximated values for all belens provided by vendor
        self.l = 7.e-4 # 700 um
        self.d = 60.e-6 # 60 um
        # constant distances
        self.distUndulatortoTCC = 410
        self.distIPM1toTCC = 66.55  # from XRT lens to TCC # 66.55
        self.distIPM1toMECLens = 62.55 # from MEC lens to XRT lens
        self.distMECLensToTCC = 4.0 # from mec belens to TCC

        xdelta= np.array(sorted(self.delta.keys()))
        ydelta= []
        for i in xdelta:      
            ydelta.append(self.delta[i])
        ydelta = np.array(ydelta)
        self.funcInterpolationDelta = interp1d(xdelta, ydelta )

        xbeta= np.array(sorted(self.beta.keys()))
        ybeta= []
        for i in xbeta:
            ybeta.append(self.beta[i])
        ybeta = np.array(ybeta)
        self.funcInterpolationBeta = interp1d(xbeta, ybeta )
 
    def computeSingleLensFocalLength(self, curvatureRadius = 1500.e-6, XRayEnergy=None):
        if XRayEnergy:
            _XRayEnergy = XRayEnergy
        else:
            _XRayEnergy = lcls_linac.getXrayeV()
        print "X-ray photon energy is %s " % _XRayEnergy
        

        # using Interpolation to get the delta and beta for different X-ray photon energy
        try:
            _delta = self.funcInterpolationDelta(_XRayEnergy)
            return curvatureRadius/2.0/_delta
            
        except ValueError:
            print "X-ray photon energy is beyond the interpolation range!"
        
    
    def computeTransmission(self,curvatureRadius = 1500.e-6, XRayEnergy=None, MecLensSet=None):
        if XRayEnergy:
            _XRayEnergy = XRayEnergy
        else:
            _XRayEnergy = lcls_linac.getXrayeV()
        print "X-ray photon energy is %s " % _XRayEnergy
        
        # profile of the Parabolic lens: y = x^2 / 2 R, here l is total thickness of lens, d is the thickness of the middle part only
        apertureRadius = math.sqrt( curvatureRadius*(self.l-self.d) )
        # distance from source to XRT lens: 410 meters from Undulator to TCC, 76.37 meters from IPM1 to TCC
        distSourceLens1 = self.distUndulatortoTCC - self.distIPM1toTCC 
        # source X-ray beam size
        sigma_0 = 46.525 * (_XRayEnergy**(-0.1414)) * (10**(-6))
        # source X-ray beam divergence
        D_0 = 4623/2.35 * (_XRayEnergy**(-0.8541)) * 10**(-6)
        # X-ray beam size at lens 1, Dm = divergence * focal length
        sigma = D_0 * distSourceLens1
        print "X-ray beam size at XRT lens: %s (m)" % sigma
        # distance from the focal plane of XRT lens to XRT lens itself
        r = ( (1/self.computeSingleLensFocalLength(curvatureRadius,_XRayEnergy) ) - (1/distSourceLens1) )**(-1)
        # image size after lens 1
        sigmaImageAfterLens1 = sigma_0 * (r/distSourceLens1)
        print "X-ray image size after lens 1: %s (m)" % sigmaImageAfterLens1
        # X-ray beam divergence after lens 1
        DAfterLens1 = D_0 * (distSourceLens1/r)
        # linear absorption
        try:
            _beta = self.funcInterpolationBeta(_XRayEnergy)
            _delta = self.funcInterpolationDelta(_XRayEnergy)  
        except ValueError:
            print "X-ray photon energy is beyond the interpolation range!" 
        mu = 4 * math.pi * _XRayEnergy * (10**10) / self.lambdaToE * _beta
        # compute transmisstion after lens 1
        __SIGMA  = 1 / ( math.sqrt( 1/(sigma**2) + 2*mu/curvatureRadius ) )
        transmissionAfterLens1 = (__SIGMA**2)/(sigma**2) * math.exp( -1 * mu * self.d) * ( 1 - (math.exp(-1*(apertureRadius**2)/(2*(__SIGMA**2))) ) )
        
        print "X-ray transmission after XRT lens: %s "  % transmissionAfterLens1
        # compute transmission after lens 2

        nLensMEC = 0 # 3.5, approximation of number of lens in the MEC compound refractive lens
        curvatureRadiusMEC = 500e-6
        curvatureRadiusMECtotal =  0.
        #curvatureRadiusMECtotal = curvatureRadiusMEC / nLensMEC
        # focal length for MEC belens
        #focalLengthMEC = curvatureRadiusMECtotal / 2 / _delta
        
        if MecLensSet is not None:
            _lens_set = MecLensSet
        else:
            #_lens_set = [3 , 500e-6, 1, 300e-6]
            _lens_set = [4 , 500e-6, 3, 300e-6]
            #_lens_set = [2 , 500e-6, 10, 300e-6]

        for i in range(len(_lens_set)/2):
            nLensMEC += _lens_set[2*i]
            curvatureRadiusMECtotal += 1. / _lens_set[2*i+1]
        curvatureRadiusMECtotal = 1./curvatureRadiusMECtotal

        focalLengthMEC = calcFocalLength(_XRayEnergy/1000.,_lens_set)
        print 'focal length of MEC lens is %s m' % (focalLengthMEC)

        

        # distance from image to MEC lens
        distanceFocalPlaneToMECLens = 1 / (  1/focalLengthMEC + 1/(r-self.distIPM1toMECLens)  ) # 72.37 meters = distance from MEC lens to IPM1
        # aperture size of MEC lens
        apertureRadiusMEC = math.sqrt( curvatureRadiusMEC*(self.l-self.d) )
        # X-ray beam size at MEC lens
        sigmaMEC = DAfterLens1 * (r-self.distIPM1toMECLens)
        print 'X-ray beam size at MEC lens: %s m' % (sigmaMEC)
        # X-ray image size after MEC lens
        sigmaImageAfterLens2 = sigmaImageAfterLens1 * focalLengthMEC / (r-self.distIPM1toMECLens)
        print 'X-ray focal spot size after MEC lens: %s m' % (sigmaImageAfterLens2)

        # project to spot size at TCC
 
        sigmaImageAfterLens2AtTCC =  sigmaMEC  * (  ( focalLengthMEC - self.distMECLensToTCC) / focalLengthMEC  ) if focalLengthMEC > self.distMECLensToTCC else sigmaMEC * ( (self.distMECLensToTCC-focalLengthMEC) / focalLengthMEC )
        print 'X-ray beam size at TCC is %s: m' % ( sigmaImageAfterLens2AtTCC )
        
        # X-ray divergence after MEC lens
        DAfterLens2 = DAfterLens1 * ((r-self.distIPM1toMECLens)/focalLengthMEC) 
        # linear absorption coeff. is still mu
        dTotal = self.d * nLensMEC
        
        __SIGMAMEC  = 1 / ( math.sqrt( 1/(sigmaMEC**2) + 2*mu/curvatureRadiusMECtotal ) )
        # transmission of MEC lens
        transmissionAfterLens2 = (__SIGMAMEC**2)/(sigmaMEC**2) * math.exp( -1 * mu * dTotal) * ( 1 - (math.exp(-1*(apertureRadiusMEC**2)/(2*(__SIGMAMEC**2))) ) )


        transmissionAfterBothLens = transmissionAfterLens1 * transmissionAfterLens2
        print "total transmission of both XRT lens and MEC lens is: ", transmissionAfterBothLens
