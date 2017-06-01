from __future__ import with_statement
"""
Remote control of the MAR CCD detector, using Michael Blum's sample remote
control server program "marccd_server_socket" with TCP port number 2222.

Usage example: ccd = marccd("marccd043.cars.aps.anl.gov:2222")

The server is started from the MarCCD software from the Remote Control
control panel with the second parameter ("Server command" or "Device Database
Server") set to "/home/marccdsource/servers/marccd_server_socket", and the third parameter
("Server Arguments" or "Personal Name") set to "2222".

The server understand the following commands:
start - Puts the CCD to integration mode, no reply
readout,0,filename - Reads out the detector, corrects the image and saves it to a file
  no reply
readout,1 - reads a new background image, no reply
get_state - reply is integer number containing 6 4-bit fields
  bits 0-3: state: 0=idle,8=busy
  bits 4-7: acquire
  bits 8-11: read
  bits 12-15: correct
  bits 16-19: write 
  bits 20-23: dezinger 
  Each filed contains a 4-bit code, with the following meaning: 
  0=idle, 1=queued, 2=executing, 4=error 
  The exception is the 'state' field, which has only 0=idle and 8=busy.
writefile,<filename>,1 - Save the last read image, no reply
set_bin,8,8 - Use 512x512-pixel bin mode, no reply
set_bin,2,2 - Use full readout mode (2048x2048 pixels), no reply
  (The 1x1 bin mode with 4096x4096 pixels is not used, because the point-spread
  function of the fiber optic taper is large compared to the pixel size)
get_bin - reply is two integer numbers, e.g. "2,2"
get_size_bkg - reply is the number of pixels of current the background image, e.g. "2048,2048"

Reference: MARCCD Software Manual, v 0.10.17 (2006), Appendix 3: The remote mode
of marccd.
Friedrich Schotte, NIH, 10 Aug 2007 - APS, 16 Mar 2010
"""

import socket
from time import sleep,time
from thread import allocate_lock

__version__ = "2.0"

class marccd(object):
  """This is to remote control the MAR CCD detector
  Using remote protocol version 1"""

  def __init__(self,ip_address="marccd043.cars.aps.anl.gov:2222"):
    """ip_address may be given as address:port. If :port is omitted, port
    number 2222 is assumed."""
    object.__init__(self)
    self.timeout = 1.0
    if ip_address.find(":") >= 0:
      self.ip_address = ip_address.split(":")[0]
      self.port = int(ip_address.split(":")[1])
    else: self.ip_address = ip_address; self.port = 2222
    self.connection = None # network connection
    # This is to make the query method multi-thread safe.
    self.lock = allocate_lock()
    # If this flag is set 'start' automatically reads a background image
    # if there is not valid backgournd image.
    self.auto_bkg = False
    # Whether to save corrected or raw images.
    self.save_raw = False
    # Keep track of when the detector was last read.
    self.last_read = 0.0
    # Verbose logging: record verey command and reply in /tmp/marccd.log
    self.verbose_logging = False
    self.retries = 2 # used in case of communation error

  def write(self,command):
    """Sends a command to the oscilloscope that does not generate a reply,
    e.g. "ClearSweeps.ActNow()" """
    if len(command) == 0 or command[-1] != "\n": command += "\n"
    self.log("write %r" % command)
    with self.lock: # Allow only one thread at a time inside this function.
      for attempt in range(0,self.retries):
        try:
          if self.connection == None:
            self.connection = socket.socket()
            self.connection.settimeout(self.timeout)
            self.connection.connect((self.ip_address,self.port))
          print command
          self.connection.sendall (command)
          return
        except Exception,message:
          self.log_error("write %r attempt %d/%d failed: %s" %
              (command,attempt+1,self.retries,message))
          self.connection = None

  def query(self,command):
    """To send a command that generates a reply, e.g. "InstrumentID.Value".
    Returns the reply"""
    self.log("query %r" % command)
    if len(command) == 0 or command[-1] != "\n": command += "\n"
    with self.lock: # Allow only one thread at a time inside this function.
      for attempt in range(0,self.retries):
        try:
          if self.connection == None:
            self.connection = socket.socket()
            self.connection.settimeout(self.timeout)
            self.connection.connect((self.ip_address,self.port))
          self.connection.sendall (command)
          reply = self.connection.recv(4096)
          while reply.find("\n") == -1:
            reply += self.connection.recv(4096)
          self.log("reply %r" % reply)
          return reply.rstrip("\n\0")
        except Exception,message:
          self.log_error("write %r attempt %d/%d failed: %s" %
              (command,attempt+1,self.retries,message))
          self.connection = None
      return ""

  def query_long(self,command):
    """To send a command that generates a reply of more than 80 bytes.
    Returns the reply"""
    self.log("query %r" % command)
    if len(command) == 0 or command[-1] != "\n": command += "\n"
    with self.lock: # Allow only one thread at a time inside this function.
      for attempt in range(0,self.retries):
        try:
          if self.connection == None:
            self.connection = socket.socket()
            self.connection.settimeout(self.timeout)
            self.connection.connect((self.ip_address,self.port))
          self.connection.sendall (command)
          reply = self.connection.recv(4096)
          self.connection.settimeout(0.1)
          while True:
            try: reply += self.connection.recv(4096)
            except socket.timeout: break
          self.log("reply length %r" % len(reply))
          return reply
        except Exception,message:
          self.log_error("write %r attempt %d/%d failed: %s" %
              (command,attempt+1,self.retries,message))
          self.connection = None
      return ""

  def state_code(self):
    "returns the status code as interger value"
    reply = self.query("get_state").strip("\n\0")
    try: status = int(eval(reply))
    except Exception,message:
      self.log_error("command 'get_state' generated bad reply %r: %s" % (reply,message))
      return 0
    # bit 8 and 9 of the state code tell whether the task status of "read"
    # is either "queued" or "executing"
    if (status & 0x00000300) != 0: self.last_read = time()
    return status

  def is_idle (self):
    return (self.state_code() == 0)

  def is_integrating (self):
    "tells whether the chip is integrating mode (not reading, not clearing)"
    # "acquire" field is "executing"
    return ((self.state_code() & 0x00000020) != 0)

  def is_reading (self):
    "tells whether the chip is currently being read out"
    # bit 8 and 9 of the state code tell whether the task status of "read"
    # is either "queued" or "executing"
    return ((self.state_code() & 0x00000300) != 0)
    
  def is_correcting (self):
    "tells whether the chip is currently being read out"
    # bit 8 and 9 of the state code tell whether the task status of "correct"
    # is either "queued" or "executing"
    return ((self.state_code() & 0x00003000) != 0)

  def state(self):
    "readble status information: idle,integating,reading,writing"
    try: status = self.state_code()
    except: return ""
    # bit mask 0x00444440 masks out error flags
    if (status & ~0x00444440) == 0: return "idle"
    if (status & 0x00000020) != 0: return "integrating"
    if (status & 0x00000200) != 0: return "reading"
    if (status & 0x00002000) != 0: return "correcting"
    if (status & 0x00020000) != 0: return "writing"
    if (status & 0x00200000) != 0: return "dezingering"
    return ""

  def start(self):
    """Puts the detector into inegration mode by stopping the continuous
    clearing.
    In case the CCD readout is in progess, execution is delayed until the
    last readout is finished.
    This also acquires a background image, in case there is no valid background
    image (after startup or binning changed).
    """
    # Wait for the readout of the previous image to finish.
    while self.is_reading(): sleep(0.05)
    if self.auto_bkg:
      # Make sure there is a valid background image. Otherwise, the image
      # correction will fail.
      self.update_bkg() 
    self.write("start")
    while not self.is_integrating(): sleep (0.05)

  def readout(self,filename=None):
    """Reads the detector.
    If a filename is given, the image is saved as a file.
    The image file is written in background as a pipelined operation.
    The function returns immediately.
    The pathname of the file is interpreted in file system of the server,
    not locally.
    If 'save_raw' is true (default: false), the image raw data is saved
    rather than the correct image.
    """
    if not self.save_raw:    
      if filename != None: 
        self.write("readout,0,"+remote(filename))
      else: self.write("readout,0")
    else:
      if filename != None: self.write("readout,3,"+remote(filename))
      else: self.write("readout,3")
    while not self.is_reading(): sleep(0.05)
    self.last_read = time()

  def readout_and_save_raw(self,filename):
    """Reads the detector and saves the uncorrected image as a file.
    The image file is written in background as a pipelined operation.
    The function returns immediately.
    The pathname of the file is interpreted in file system of the server,
    not locally.
    """
    self.write("readout,3,"+remote(filename))
    self.last_read = time()

  def readout_raw(self):
    "Reads the detector out without correcting and displaying the image."
    self.write("readout,3")
    self.last_read = time()

  def save_image(self,filename): 
    """Saves the last read image to a file.
    The pathname of the file is interpreted in file system of the server,
    not locally.
    """
    self.write("writefile,"+remote(filename)+",1")

  def save_raw_image(self,filename):
    """Saves the last read image without spatial and uniformity correction
    to a file.
    The pathname of the file is interpreted in file system of the server,
    not locally.
    """
    self.write("writefile,"+remote(filename)+",0")

  def image(self):
    """Returns the last image as 16-bit raw data.
    This command required a special version of the MAR CCD server
    (/home/marccd/NIH/v1/marccd_server_socket)
    """
    return self.query_long("get_image,1")
  
  def raw_image(self):
    """Returns the last read image before correction as 16-bit raw data.
    This command required a special version of the MAR CCD server
    (/home/marccd/NIH/v1/marccd_server_socket)
    """
    return self.query_long("get_image,0")

  def read_image(self):
    """Reads the detector and transfers the image without saving to a file.
    Returns 16-bit raw data.
    This command required a special version of the MAR CCD server
    (/home/marccd/NIH/v1/marccd_server_socket)
    """
    self.write("readout,0")
    sleep(0.2)
    while self.is_correcting(): sleep(0.2)
    return self.query_long("get_image,1")
    self.last_read = time()
  
  def read_raw_image(self):
    """Reads the detector and transfers the image without saving to a file.
    Returns 16-bit raw data.
    This command required a special version of the MAR CCD server
    (/home/marccd/NIH/marccd_server_socket)
    """
    self.write("readout,3")
    sleep(0.2)
    while self.is_reading(): sleep(0.2)
    return self.query_long("get_image,0")
    self.last_read = time()

  def get_bin_factor(self): 
    try: return int(self.query("get_bin").split(",")[0])
    except: return
  def set_bin_factor(self,n):
    self.write("set_bin,"+str(n)+","+str(n))
    # After a bin factor change it takes about 2 s before the new
    # bin factor is read back.
    t = time()
    while self.get_bin_factor() != n and time()-t < 3: sleep (0.1) 

  bin_factor = property(get_bin_factor,set_bin_factor,
    doc="Readout X and Y bin factor")

  def read_bkg(self):
    """Reads a fresh the backgound image, which is substracted from every image after
    readout before the correction is applied.
    """
    self.write("start")
    while not self.is_integrating(): sleep(0.05)
    self.write("readout,1")
    while not self.is_idle(): sleep(0.05)
    self.last_read = time()

  def image_size(self):
    "Width and height of the image in pixels at the current bin mode"
    try: return int(self.query("get_size").split(",")[0])
    except: return 0

  def bkg_image_size(self): # does not work with protocol v1 (timeout)
    """Width and height of the current background image in pixels.
    This value is important to know if the bin factor is changed.
    If the backgroud image does not have the the same number of pixels
    as the last read image the correction as saving to file will fail.
    At startup, the background image is empty and this value is 0.
    """
    try: return int(self.query("get_size_bkg").split(",")[0])
    except: return 0

  def update_bkg(self):
    """Updates the backgound image if needed, for instance after the server has
    been restarted or after the bin factor has been changed.
    """
    if not self.bkg_valid(): self.read_bkg()

  def bkg_valid(self):
    return self.bkg_image_size() == self.image_size()

  def state_info(self,status):
    """Decode the reply of te 'get_state" command.
    status is an integer number."""
    # reply is integer number containing 6 4-bit fields
    # bits 0-3: state: 0=idle,8=busy
    # bits 4-7: acquire
    # bits 8-11: read
    # bits 12-15: correct
    # bits 16-19: write 
    # bits 20-23: dezinger 
    # Each fieled contains a 4-bit code, with the following meaning: 
    # 0=idle, 1=queued, 2=executing, 4=error 
    # The exception is the 'state' field, which has only 0=idle and 8=busy.
    if type(status) == str:
      try: status = int(status.strip("\n\0"))
      except: return "status %r: not an integer" % status
    s = ""
    if (status & 0x0000000F) != 0:
      state = status & 0x0000000F
      if state == 8: s += "busy, "
      elif state != 0: s += "state %d, " % state
    if (status & 0x00000010) != 0: s += "integration queued, "
    if (status & 0x00000020) != 0: s += "integrating, "
    if (status & 0x00000040) != 0: s += "integration error, "
    if (status & 0x00000100) != 0: s += "read queued, "
    if (status & 0x00000200) != 0: s += "reading, "
    if (status & 0x00000400) != 0: s += "read error, "
    if (status & 0x00001000) != 0: s += "correct queued, "
    if (status & 0x00002000) != 0: s += "correcting, "
    if (status & 0x00004000) != 0: s += "correct error, "
    if (status & 0x00010000) != 0: s += "write queued, "
    if (status & 0x00020000) != 0: s +=  "writing, "
    if (status & 0x00080000) != 0: s +=  "write error, "
    if (status & 0x00100000) != 0: s += "dezinger queued, "
    if (status & 0x00200000) != 0: s +=  "dezingering, "
    if (status & 0x00800000) != 0: s +=  "dezinger error, "
    if (status & 0xFF000000) != 0: s +=  "(undcoumented bits 24-31 set), "
    s = s.strip(", ")
    if s == "": s = "idle"
    return s

  def log_error(self,message):
    """For error messages.
    Display the message and append it to the error log file.
    If verbose logging is enabled, it is also added to the transcript."""
    from sys import stderr
    if len(message) == 0 or message[-1] != "\n": message += "\n"
    t = timestamp()
    stderr.write("%s: %s: %s" % (t,self.ip_address,message))
    file(self.error_logfile,"a").write("%s: %s" % (t,message))
    self.log(message)

  def log(self,message):
    """For non-critical messages.
    Append the message to the transcript, if verbose logging is enabled."""
    if not self.verbose_logging: return
    if len(message) == 0 or message[-1] != "\n": message += "\n"
    t = timestamp()
    file(self.logfile,"a").write("%s: %s" % (t,message))

  def get_error_logfile(self):
    """File name error messages."""
    from tempfile import gettempdir
    return gettempdir()+"/marccd_error.log"
  error_logfile = property(get_error_logfile)

  def get_logfile(self):
    """File name for transcript if verbose logging is enabled."""
    from tempfile import gettempdir
    return gettempdir()+"/marccd.log"
  logfile = property(get_logfile)


def timestamp():
    """Current date and time as formatted ASCCI text, precise to 1 ms"""
    from datetime import datetime
    timestamp = str(datetime.now())
    return timestamp[:-3] # omit microsconds
    
def remote(pathname):
  """This converts the pathname of a file on a network file server from
  the local format to the format used on the MAR CCD compter.
  e.g. "//id14bxf/data" in Windows maps to "/net/id14bxf/data" on Unix"""
  if not pathname: return pathname
  # Try to expand a Windows drive letter to a UNC name. 
  try:
    import win32wnet
    # Convert "J:/anfinrud_0811/Data" to "J:\anfinrud_0811\Data".
    pathname = pathname.replace("/","\\")
    pathname = win32wnet.WNetGetUniversalName(pathname)
  except: pass
  # Convert separators from DOS style to UNIX style.
  pathname = pathname.replace("\\","/")

  if pathname.find("//") == 0: # //server/share/directory/file
    parts = pathname.split("/")
    if len(parts) >= 4:
      server = parts[2] ; share = parts[3]
      path = ""
      for part in parts[4:]: path += part+"/"
      path = path.rstrip("/")
      pathname = "/net/"+server+"/"+share+"/"+path
  return pathname

if __name__ == "__main__": # for testing
  ccd = marccd("con-ics-xpp-rayonix:2222")
  ccd.verbose_logging = True
