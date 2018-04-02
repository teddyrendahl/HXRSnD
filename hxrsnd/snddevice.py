"""
Common SnD device classes
"""
import logging

from ophyd.device import Device

logger = logging.getLogger(__name__)


class SndDevice(Device):
    """
    Base Sndmotor class
    """
    def __init__(self, prefix, name=None, desc=None, set_timeout=1, *args, 
                 **kwargs):
        super().__init__(prefix, name=name, *args, **kwargs)
        self.desc = desc or self.name
        self.set_timeout = set_timeout

    def _apply_all(self, method, subclass=object, *method_args, 
                   **method_kwargs):
        """
        Runs the method for all devices that are of the inputted subclass. All
        additional arguments and key word arguments are passed as inputs to the
        method.

        Parameters
        ----------
        method : str
            Method of each device to run.

        subclass : class
            Subclass to run the methods for.

        method_args : tuple, optional
            Positional arguments to pass to the method

        method_kwargs : dict, optional
            Key word arguments to pass to the method
        """
        ret = []
        # Check if each component is a subclass of subclass then run the method
        for comp_name in self.component_names:
            component = getattr(self, comp_name)
            if issubclass(type(component), subclass):
                ret.append(getattr(component, method)(*method_args,
                                                      **method_kwargs))
        return ret

    def st(self, *args, **kwargs):
        """
        Returns or prints the status of the device. Alias for 'device.status()'.
        
        Parameters
        ----------
        print_status : bool, optional
            Determines whether the dataframe should be printed or returned

        short : bool, optional
            Use a shortened list or all relevant parameters
        """
        return self.status(*args, **kwargs) 

    def __repr__(self):
        """
        Returns the status of the device. Alias for status().

        Returns
        -------
        status : str
            Status string.
        """
        # Try to return the status
        try:
            return self.status(print_status=False)
        # There is no scenario where we would want to know of an error here
        except:
            return super().__repr__()
