#! /usr/bin/env python

import sys
import os
# import time
import commands
from time import sleep

from pypslog import logprint
import XPS_C8_drivers

# list of xps controllers for each hutch
controllers = {
    'thz' : [ 'thz-1', 'thz-2', 'thz-3', 'thz-4' ],
    'fct' : [ 'fct-1', 'fct-2', 'fct-3' ],
    'lh' :  [ 'lh-1', 'lh-2' ],
    'amo' : [ 'amo-1', 'amo-2', 'amo-3' ],
    'sxr' : [ 'sxr-1', 'sxr-2' ],
    'xpp' : [ 'xpp-1', 'xpp-2' ],
    'cxi' : [ 'cxi-1' ],
    'tst' : [ 'tst-1' ],
}

# list of hosts where one should be logged in to talk to an xps
hosts = {
    'thz-1' : 'ioc-und-thz2',
    'thz-2' : 'ioc-und-thz2',
    'thz-3' : 'ioc-und-thz2',
    'thz-4' : 'ioc-und-thz2',
    'fct-1' : 'ioc-fct-thz01',
    'fct-2' : 'ioc-fct-thz01',
    'fct-3' : 'ioc-fct-thz01',
    'lh-1'  : 'ioc-und-thz2',
    'lh-2'  : 'ioc-und-thz2',
    'amo-1' : 'ioc-und-thz2',
    'amo-2' : 'ioc-und-thz2',
    'amo-3' : 'ioc-und-thz2',
    'sxr-1' : 'ioc-und-thz2',
    'sxr-2' : 'ioc-und-thz2',
    'xpp-1' : 'xpp-control',
    'xpp-2' : 'xpp-daq',
    'cxi-1' : 'cxi-control',
    'tst-1' : 'ioc-tst-exp1',
}

# the ip addresses of the xps controllers
xps_ips = {
    'thz-1' : '172.21.35.30',
    'thz-2' : '172.21.35.32',
    'thz-3' : '172.21.35.49',
    'thz-4' : '172.21.35.51',
    'fct-1' : '172.21.35.87',
    'fct-2' : '172.21.35.88',
    'fct-3' : '172.21.35.89',
    'lh-1'  : '172.21.35.28',
    'lh-2'  : '172.21.35.29',
    'amo-1' : '172.21.35.43',
    'amo-2' : '172.21.35.44',
    'amo-3' : '172.21.35.45',
    'sxr-1' : '172.21.35.67',
    'sxr-2' : '172.21.35.69',
    'xpp-1' : '172.21.38.43',
    'xpp-2' : '172.21.38.45',
    'cxi-1' : '172.21.44.53',
    'tst-1' : '172.21.42.48',
}

class XPS(XPS_C8_drivers.XPS):
    def __init__(self, xps):
        self.xps = XPS_C8_drivers.XPS()
        # TODO : raise ValueException if bad xps
        self.name = xps
        self.ip = xps_ips[xps]
        self.socket = -1

    def err_log(self, function, err):
        if (self.socket >= 0):
            Error, err_str = self.xps.ErrorStringGet (self.socket, err)
            print( "ERROR: %s: %s" % ( function, err_str ) )

    def connect(self):
        #print( "Connecting to XPS %s  (ip=%s, socket=%s) ..." % (self.name, self.ip, self.socket) )
        if (self.socket < 0):
            self.socket = self.xps.TCP_ConnectToServer(self.ip, 5001, 10)
        if (self.socket < 0):
            raise IOError( "Cannot connect to XPS: %s  IP=%s.  Did you ssh to the right host? (i.e. %s)" %
                            (self.name, self.ip, hosts[self.name] ) )
        #print( "Connected:  socket = %d" % self.socket )

    def close(self):
        print( "Disconnectiong ...XPS %s  (ip=%s, socket=%s) ..." % (self.name, self.ip, self.socket ) )
        if (self.socket >= 0):
            self.xps.TCP_CloseSocket(self.socket)
            self.socket = -1  #####  Added by David

    def __del__(self):
        # if (self.socket >= 0):
            # self.close()
        pass

    def get_socket(self):
        if (self.socket < 0):
            self.connect()
        return self.socket
        

class Motor:
    def __init__(self, xps, group=1,name=None):
        """ xps is 'thz-1', 'lh-2', 'amo-1', ,,,
            group is the motor number in the range 1..8"""

        #print "xps = %s" % xps
        #print "group = %s" % group

        self.xps = xps
        self.socket = self.xps.get_socket()
        if (name is None):
          self.group = group
          self.name = "GROUP" + str(group)
          self.positioner = self.name + ".POSITIONER"
        else:
          self.group = group
          self.name =  group
          self.positioner = group+"."+self.name
        #print "Socket = %d" % self.socket
        #print "Name = %s" % self.name

    def close(self):
        self.xps.close()

    def connect(self):
        self.xps.connect()

    def get_status(self):
        # print dir(self.xps)
        err, stat = self.xps.GroupStatusGet(self.socket, self.name)
        # if err < 0: self.err_log("GroupStatusGet", err)
        return err if err < 0 else stat
    stat = property(get_status)

    def get_status_str(self, status):
        if status < 0:
            err, status_str = self.xps.ErrorStringGet(self.socket, status)
        else:
            err, status_str = self.xps.GroupStatusStringGet(self.socket, status)
        if err < 0: self.err_log("GroupStatusGet", err)
        return "" if err < 0 else status_str

    def wait(self):
      while (self.get_status() != 12):
        sleep(0.001)

    def get_position(self):
        err, position = self.xps.GroupPositionCurrentGet(self.socket, self.name, 1)
#        if err < 0:
#            self.err_log("GroupPositionCurrentGet", err)
#            position = 0.0
        return position

    def get_velocity(self):
        err, velocity, acceleration, minJerkTime, maxJerkTime = self.xps.PositionerSGammaParametersGet(self.socket, self.positioner)
        if err < 0:
            self.err_log("PositionerSGammaParametersGet", err)
            return err
        return velocity

    def get_acceleration(self):
        err, velocity, acceleration, minJerkTime, maxJerkTime = self.xps.PositionerSGammaParametersGet(self.socket, self.positioner)
        if err < 0:
            self.err_log("PositionerSGammaParametersGet", err)
            return err
        return acceleration

    def set_velocity(self, value):
        err, velocity, acceleration, minJerkTime, maxJerkTime = self.xps.PositionerSGammaParametersGet(self.socket, self.positioner)
        if err < 0:
            self.err_log("PositionerSGammaParametersGet", err)
            return err
        velocity = value
        err = self.xps.PositionerSGammaParametersSet(self.socket, self.positioner, velocity, acceleration, minJerkTime, maxJerkTime)
        if err < 0:
            self.err_log("PositionerSGammaParametersSet", err)
            return err
        return velocity

    def set_acceleration(self, value):
        err, velocity, acceleration, minJerkTime, maxJerkTime = self.xps.PositionerSGammaParametersGet(self.socket, self.positioner)
        if err < 0:
            self.err_log("PositionerSGammaParametersGet", err)
            return err
        acceleration = value
        err = self.xps.PositionerSGammaParametersSet(self.socket, self.positioner, velocity, acceleration, minJerkTime, maxJerkTime)
        if err < 0:
            self.err_log("PositionerSGammaParametersSet", err)
            return err
        return acceleration


    def get_lo_limit(self):
        # print "get_lo_limit()"
        if self.stat >= 0:
            err, lo_limit, hi_limit = self.xps.PositionerUserTravelLimitsGet(self.socket, self.positioner)
            # print "got limits: %f %f ..." % (lo_limit, hi_limit)
            if err < 0: self.err_log("PositionerUserTravelLimitsGet", err)
            # print "PositionerUserTravelLimitsGet returned err=%d" % err
        else:
            lo_limit = 0.0
        # print " ==> %f" % lo_limit
        return lo_limit

    def set_lo_limit(self, value):
        # print "set_lo_limit(%f)" % value
        lo_limit = value
        hi_limit = self.get_hi_limit()
        # print "hi_limit = %f" % hi_limit
        if self.stat >= 0:
            # print "setting limits: %f %f ..." % (lo_limit, hi_limit)
            err = self.xps.PositionerUserTravelLimitsSet(self.socket, self.positioner, lo_limit, hi_limit)
            if err < 0: self.err_log("PositionerUserTravelLimitsSet", err)
        # FIXME -- when err < 0
        return value

    def get_hi_limit(self):
        # print "get_hi_limit()"
        if self.stat >= 0:
            err, lo_limit, hi_limit = self.xps.PositionerUserTravelLimitsGet(self.socket, self.positioner)
            # print "got limits: %f %f ..." % (lo_limit, hi_limit)
            if err < 0: self.err_log("PositionerUserTravelLimitsGet", err)
        else:
            hi_limit = 0.0
        # print " ==> %f" % hi_limit
        return hi_limit

    def set_hi_limit(self, value):
        # print "set_hi_limit(%f)" % value
        lo_limit = self.get_lo_limit()
        hi_limit = value
        # print "setting hi_limit to %f" % hi_limit
        # print "lo_limit = %f" % lo_limit
        if self.stat >= 0:
            # print "setting limits: %f %f ..." % (lo_limit, hi_limit)
            err = self.xps.PositionerUserTravelLimitsSet(self.socket, self.positioner, lo_limit, hi_limit)
            if err < 0: self.err_log("PositionerUserTravelLimitsSet", err)
        # FIXME -- when err < 0
        return value

    def err_log(self,k,msg):
      logprint("%s: %s" % (k,msg))

    def reboot(self):
        print "Rebooting controller ..."
        err = self.xps.Reboot(self.socket)
        if err < 0: self.err_log("Reboot", err)

    def kill(self):
        err = self.xps.GroupKill(self.socket, self.name)
        if err < 0: self.err_log("GroupKill", err)

    def init(self):
        print "Initializing %s %s ..." % ( self.xps.name, self.name )
        err, fnct = self.xps.GroupInitialize(self.socket, self.name)
        if err < 0: self.xps.err_log("GroupInitialize", err)
        return err

    def home(self):
        err = self.xps.GroupHomeSearch(self.socket, self.name)
        if err < 0: self.err_log("GroupHomeSearch", err)

    def move(self, position):
        positions = [ position ]
        err = self.xps.GroupMoveAbsoluteNoWait(self.socket, self.name, positions)
        if err < 0: self.err_log("GroupMoveAbsolute", err)

    def move_and_wait_lim(self, position):
      if (position>self._lowlim) and (position<self._highlim):
        self.move_and_wait(position)
      else "Requested position outside soft limits! %s won't move" %self.name

    
    def move_and_wait(self, position):
        positions = [ position ]
        err = self.xps.GroupMoveAbsolute(self.socket, self.name, positions)
        if err < 0: self.err_log("GroupMoveAbsolute", err)

    def move_rel(self, displacement):
        displacements = [ displacement ]
        err = self.xps.GroupMoveRelative(self.socket, self.name, displacements)
        if err < 0: self.err_log("GroupMoveRelative", err)

    def enable(self):
        err = self.xps.GroupMotionEnable(self.socket, self.name)
        if err < 0: self.err_log("GroupMotionEnable", err)

    def disable(self):
        err = self.xps.GroupMotionDisable(self.socket, self.name)
        if err < 0: self.err_log("GroupMotionDisable", err)

    def stop(self):
        err = self.xps.GroupMoveAbort(self.socket, self.name)
        if err < 0: self.err_log("GroupMoveAbort", err)

    def __str__(self):
        # print "Printing group"
        status = self.get_status()
        status_str = self.get_status_str(status)
        if status < 0:
            return "%s-%d  %s" % (self.xps.name, self.group, status_str)
        else:
            position = self.get_position()
            velocity = self.get_velocity()
            acceleration = self.get_acceleration()
            lo_lim = self.get_lo_limit()
            hi_lim = self.get_hi_limit()
            return "%s-%s  stat= %3d  pos= %8.4f  vel= %7.3f  acc= %7.3f lolim= %8.4f  hilim= %8.4f  %s" \
                % (self.xps.name, self.group, status, position, velocity, acceleration, lo_lim, hi_lim, status_str)


def set_val(xps, mtr, cmd, val):
    if (cmd == 'vel'):
        m = Motor( xps, mtr )
        m.set_velocity(val)
    elif (cmd == 'acc'):
        m = Motor( xps, mtr )
        m.set_acceleration(val)
    elif (cmd == 'lolim'):
        m = Motor( xps, mtr )
        m.set_lo_limit(val)
    elif (cmd == 'hilim'):
        m = Motor( xps, mtr )
        m.set_hi_limit(val)

    elif (cmd == 'move'):
        m = Motor( xps, mtr )
        m.move(val)
    elif (cmd == 'mover'):
        m = Motor( xps, mtr )
        m.move_rel(val)
    else:
        usage()

def get_val(xps, mtr, cmd):
    if (cmd == 'stat'):
        m = Motor( xps, mtr )
        s =  m.get_status()
        print "%s: %s" % ( s, m.get_status_str(s) )
    elif (cmd == 'pos'):
        m = Motor( xps, mtr )
        print m.get_position()
    elif (cmd == 'vel'):
        m = Motor( xps, mtr )
        print m.get_velocity()
    elif (cmd == 'acc'):
        m = Motor( xps, mtr )
        print m.get_acceleration()
    elif (cmd == 'lolim'):
        m = Motor( xps, mtr )
        print m.get_lo_limit()
    elif (cmd == 'hilim'):
        m = Motor( xps, mtr )
        print m.get_hi_limit()

    elif (cmd == 'reboot'):
        m = Motor( xps, mtr )
        m.reboot()
    elif (cmd == 'kill'):
        m = Motor( xps, mtr )
        m.kill()
        ls_mtr(xps, mtr)
    elif (cmd == 'init'):
        m = Motor( xps, mtr )
        m.init()
        ls_mtr(xps, mtr)
    elif (cmd == 'home'):
        m = Motor( xps, mtr )
        m.home()
        ls_mtr(xps, mtr)
    elif (cmd == 'enable'):
        m = Motor( xps, mtr )
        m.enable()
        ls_mtr(xps, mtr)
    elif (cmd == 'disable'):
        m = Motor( xps, mtr )
        m.disable()
    else:
        pass

def ls_mtr(xps, mtr):
    try:
        m = Motor( xps, mtr )
        print m
    except IOError, msg:
        print msg

def ls_mtrs_xps(xps):
    motors = range(1,9)
    for mtr in motors:
        ls_mtr(xps, mtr)

def ls_mtrs_hutch(hutch):
    for xps in controllers[hutch]:
        ls_mtrs_xps(xps)

def ls_mtrs_all():
    for hutch in [ 'thz', 'fct', 'lh', 'amo', 'sxr', 'xpp' ]:
        ls_mtrs_hutch(hutch)

def usage():
    print 'Usage:  ' + sys.argv[0] + ' [xps [mtr [cmd [val]]]]'
    print '        xps : thz-1..4, fct-1..3, lh-1..2, amo-1..3, sxr-1..2, xpp-1..2, tst-1'
    print '        mtr : 1 to 8'
    print '        cmd : init, home, kill, vel, acc, lolim, hilim, move, mover'
    print '        val : position, displacement, new limit value'
    sys.exit(1)


def ssh_to_proper_host(xps):

    myhost = commands.getoutput("hostname")

    if controllers.has_key(xps):
        desired_host = hosts[xps + "-1"]
    else:
        desired_host = hosts[xps]

    if desired_host != myhost:
        # ssh to ioc-und-thz2 and execute current command line there
        sys.argv[0] = os.path.abspath(sys.argv[0])
        cmd = ' '.join(sys.argv)
        ssh_cmd = "ssh %s %s" % (desired_host, cmd)
        out = commands.getoutput("ssh pslogin " + ssh_cmd)
        print out
        sys.exit(0)
    else:
        pass


if __name__ == "__main__":    # for testing

    # default arguments
    xps = None
    mtr = None
    cmd = None
    val = None

    # parse command line arguments
    argc = len(sys.argv)
    if (argc == 5):
        val = sys.argv[4]
    if (argc >= 4):
        cmd = sys.argv[3]
    if (argc >= 3):
        mtr = sys.argv[2]
    if (argc >= 2):
        xps = sys.argv[1]
    else:
        usage()

    ssh_to_proper_host(xps)

    # do the work
    if (val != None):
        set_val(xps, mtr, cmd, val)
        ls_mtr(xps, mtr)
    elif (cmd != None):
        get_val(xps, mtr, cmd)
    elif (mtr != None):
        ls_mtr(xps, int(mtr))
    elif (xps != None):
        if controllers.has_key(xps):
            ls_mtrs_hutch(xps)
        else:
            ls_mtrs_xps(xps)
    else:
        ls_mtrs_all()

    sys.stdout.flush()
    sys.exit(0)

# vim:syntax=python
