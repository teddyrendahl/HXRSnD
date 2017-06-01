import pypsepics
from utilities import estr
class Xraystopper:
	def __init__(self,pv="PPS:NEH1:3:SH1STPRSUM",desc="H3-FEE-stopper"):
		self.pvname = pv
		self.__desc = desc
	def __repr__(self):
		return "%s status: %s" % (self.__desc,self.status())

	def isin(self):
	       	v=pypsepics.get(self.pvname)	
                if ((v == 4)|(v==1)): return  True
		else: return False
	def status(self):
		v=pypsepics.get(self.pvname)
		if (v == 0):
			ret = "OUT"
		elif ((v == 4)|(v==1)):
			ret = "IN"
		else:
			ret = "Inconsistent"

                if ( ret == "OUT" ):
                    ret=estr(ret,color="green",type='normal')
	        else:
		    ret=estr(ret,color="red",type="normal")

		return ret 
