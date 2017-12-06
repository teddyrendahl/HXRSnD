"""
Script to hold functions copied over from blutils that pertain to computing
the bragg angle of the HXRSnD crystals.
"""
############
# Standard #
############
import logging

###############
# Third Party #
###############
import numpy as np

########
# SLAC #
########

##########
# Module #
##########

logger = logging.getLogger(__name__)

# Globals

_manual_energy = None

# Chemical Formula Aliases
alias={'Air':'N1.562O.42C.0003Ar.0094',
       'air':'N1.562O.42C.0003Ar.0094',
       'YAG':'Y3Al5O12',
       'yag':'Y3Al5O12',
       'Sapphire':'Al2O3',
       'sapphire':'Al2O3',
}

# Crystal Lattice parameters (a, b, c, alpha, beta, gamma)
# a,b,c in angstroms
# alpha, beta, gamma in degrees
lattice_parameters = {
     'Si':(5.4310205,5.4310205,5.4310205,90,90,90),
}

#define units and constants
u = {
    'ang': 1e10,
}

# Trigonometric Functions

def sind(A):
    """ 
    Sin of an angle specified in degrees.
    
    Parameters
    ----------
    A : float
        Angle in degrees.

    Returns
    -------
    x : float
        Sin of the angle.
    """
    Arad = np.deg2rad(A)
    x = np.sin(Arad) 
    return x
 
def cosd(A):
    """ 
    Cos of an angle specified in degrees.
    
    Parameters
    ----------
    A : float
        Angle in degrees.

    Returns
    -------
    x : float
        Cos of the angle.
    """
    Arad = np.deg2rad(A)
    x = np.cos(Arad) 
    return x

def tand(A):
    """ 
    Tan of an angle specified in degrees.
    
    Parameters
    ----------
    A : float
        Angle in degrees.

    Returns
    -------
    x : float
        Tan of the angle.
    """
    Arad = np.deg2rad(A)
    x = np.tan(Arad) 
    return x
 
def asind(x):
    """ 
    Calculates the arcsin in degrees.

    Parameters
    ----------
    x : float
        Value to calculate arcsin of.

    Returns
    -------
    A : float
        Arcsin of the value in degrees.
    """
    A = np.arcsin(x)
    A = np.rad2deg(A) 
    return A
 
def acosd(x):
    """ 
    Calculates the arccos in degrees.

    Parameters
    ----------
    x : float
        Value to calculate arccos of.

    Returns
    -------
    A : float
        Arccos of the value in degrees.
    """    
    A = np.arccos(x)
    A = np.rad2deg(A) 
    return A

def atand(x):
    """ 
    Calculates the arctan in degrees.

    Parameters
    ----------
    x : float
        Value to calculate arctan of.

    Returns
    -------
    A : float
        Arctan of the value in degrees.
    """    
    A = np.arctan(x)
    A = np.rad2deg(A) 
    return A

# Frequency, wavelength and energy conversions

def lam(E, o=0):
    """ 
    Computes photon wavelength in m
    
    Parameters
    ----------
    E : float
        The input energy in eV or KeV
    
    o : float, optional
        Set o to 0 if working at sub-100 eV energies

    Returns
    -------
    lam : float
        Input energy converted to wavelength
    """
    if o:
        E=E
    else:
        E=eV(E)
    lam=(12398.4/E)/u['ang']
    return lam

def lam2E(l):
    """
    Computes photon energy in eV

    Parameters
    ----------    
    l : float
        Photon wavelength in m
    
    Returns
    -------
    E : float
        Energy in eV
    """
    E = 12398.4/(l*u['ang'])
    return E

def lam2f(l):
    """
    Computes the photon frequency in Hz

    Parameters
    ----------    
    l : float
        Photon wavelength in m
    
    Returns
    -------
    f : float
        Frequency in Hz
    """
    f = 299792458/l
    return f    

# Higher level functions

def eV(E):
    """
    Returns photon energy in eV if specified in eV or KeV. Assumes that any
    value that is less than 100 is in KeV.

    Parameters
    ----------
    E : float
        The input energy to convert to eV

    Returns
    -------
    E : float
        Energy converted to eV from KeV    
    """
    if E < 100:
        E *= 1000.0
    return float(E)

def check_id(ID):
    """
    Checks to see if you are using an alias. Returns the chemical formula

    Parameters
    ----------
    ID : str
        The desired ID

    Returns
    id : str
        The full ID name from the alias dictionary or just ID
    """
    try:
        return alias[ID]
    except KeyError:
        return ID

def get_e(energy=None, correct_ev=True):
    """
    Get working energy

    Parameters
    ----------
    energy : float or None, optional
        If energy passed in, return it, otherwise return manual_energy if set,
        or machine energy otherwise.

    correct_ev : bool, optional
        Convert to eV if True

    Returns
    -------
    en : float
        The desired working energy
    """
    en = None
    if energy is not None:
        en = energy
    elif _manual_energy is not None:
        en = _manual_energy
    if correct_ev:
        en = eV(en)
    return en

def d_space(ID, hkl):
    """
    Computes the d spacing (m) of the specified material and reflection 

    Parameters
    ----------
    ID : str
        Chemical fomula : 'Si'

    hlk : tuple
        The reflection : (2,2,0)

    Returns
    -------
    d : float
        The d-spacing of the crystal using the inputted reflection.
    """
    ID = check_id(ID)
    h = hkl[0]
    k = hkl[1]
    l = hkl[2]

    lp = lattice_parameters[ID]
    a = lp[0]/u['ang']
    b = lp[1]/u['ang']
    c = lp[2]/u['ang']
    alpha = lp[3]
    beta = lp[4]
    gamma = lp[5]

    ca = cosd(alpha)
    cb = cosd(beta)
    cg = cosd(gamma)
    sa = sind(alpha)
    sb = sind(beta)
    sg = sind(gamma)

    invdsqr = 1 / (1.+2.*ca*cb*cg-ca**2.-cb**2.-cg**2.) * \
      (h**2.*sa**2./a**2. + k**2.*sb**2./b**2. + l**2.*sg**2./c**2. +
       2.*h*k*(ca*cb-cg)/a/b+2.*k*l*(cb*cg-ca)/b/c+2.*h*l*(ca*cg-cb)/a/c)
      
    d = invdsqr**-0.5
    return d

def bragg_angle(E=None, ID="Si", hkl=(2,2,0)):
    """
    Computes the Bragg angle (deg) of the specified material, reflection and
    photon energy.

    Parameters
    ----------
    E : float, optional
        Photon energy in eV or keV (default is LCLS value)

    ID : str, optional
        Chemical fomula : 'Si'

    hlk : tuple, optional
        The reflection : (2,2,0)

    Returns
    -------
    two_theta : float
        Expected bragg angle
    """
    ID = check_id(ID)
    E = get_e(energy=E, correct_ev=False)
    d = d_space(ID, hkl)
    two_theta = asind(lam(E)/2/d)
    return two_theta

def bragg_energy(theta, ID="Si", hkl=(2,2,0)):
    """
    Computes the photon energy that satisfies the Bragg condition of the
    specified material, reflection and theta angle.

    Parameters
    ----------
    theta : float, optional
        The scattering angle in degrees
    
    ID : str, optional
        Chemical fomula : 'Si'

    hlk : tuple, optional
        The reflection : (2,2,0)

    Returns
    -------
    E : float, optional
        Photon energy in eV
    """
    ID = check_id(ID)
    d = d_space(ID, hkl)
    l = 2*d*sind(theta)
    E = lam2E(l)
    return E

def snd_L(E1, E2, delay, gap=55):
    """
    Calculates the theta angles of the towers and the delay length based on the
    desired energy and delay.

    Parameters
    ----------
    E1 : float
        Energy of the delay branch in eV
    
    E2 : float
        Energy of the channel-cut branch in eV

    delay : float
        Delay of the system in picoseconds

    gap : float, optional
        Distance between the channel-cut crystals

    Returns
    -------
    theta_L : float
        The necessary angle of the delay branch in degrees.
        
    theta_cc : float
        The necessary angle of the channel-cut branch in degrees.

    L : float
        The necessary length of the delay crystals in mm.
    """
    cl = 0.3
    theta_L = bragg_angle('Si',(2,2,0),E1)
    theta_cc= bragg_angle('Si',(2,2,0),E2)
    # gap is the distance between the two faces of the channel cut crystal
    L = (delay*cl/2.+gap*(1-cosd(2*theta_cc))/sind(theta_cc))/(1-cosd(
        2*theta_L))
    logger.info("t1.L = t4.L = {} mm".format(L))
    logger.info("t1.tth = t4.tth = {} degree".format(2*theta_L))
    logger.info("t1.th1=t1.th2=t4.th1=t4.th2 = {} degree".format(theta_L))
    logger.info("t2.th=t3.th = {} degree".format(theta_cc))
    return theta_L, theta_cc, L

def snd_diag(E1, E2, delay, gap=55):
    """
    Calculates the positions of the middle diagnostics of the system based on
    the inputted energy and delay.

    Parameters
    ----------
    E1 : float
        Energy of the delay branch in eV
    
    E2 : float
        Energy of the channel-cut branch in eV

    delay : float
        Delay of the system in picoseconds

    gap : float, optional
        Distance between the channel-cut crystals

    Returns
    -------
    dd_x : float
        The necessary position of the middle delay diagnostic in mm
        
    dcc_x : float
        The necessary position of the middle channel-cut diagnostic in mm
    """
    cl = 0.3
    # speed of light
    theta_L = bragg_angle('Si',(2,2,0),E1)
    theta_cc= bragg_angle('Si',(2,2,0),E2)
    dcc_x = 2*cosd(theta_cc)*gap
    L = (delay*cl/2.+gap*(1-cosd(2*theta_cc))/sind(theta_cc))/(1-cosd(
        2*theta_L))
    dd_x = -L*sind(2*theta_L)
    logger.info("dd.x = {}".format(dd_x))
    logger.info("dcc.x = {}".format(dcc_x))
    return dd_x, dcc_x

def snd_delay(E1, E2, L, gap=55):
    """
    Calculates the delay of the system based on the inputted energies and the
    delay length.

    Parameters
    ----------
    E1 : float
        Energy of the delay branch in eV
    
    E2 : float
        Energy of the channel-cut branch in eV

    L : float
        Position of the delay crystals in mm

    Returns
    -------
    delay : float
        The delay of the system in picoseconds
    """
    cl = 0.3
    theta_L = bragg_angle('Si',(2,2,0),E1)
    theta_cc= bragg_angle('Si',(2,2,0),E2)
    delay = 2*(L*(1-cosd(2*theta_L)) - gap*(1-cosd(2*theta_cc))/sind(
        theta_cc))/cl 
    return delay

