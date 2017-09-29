"""
Script for small utility functions used in HXRSnD
"""
############
# Standard #
############
import logging
import inspect
from pathlib import Path
from collections.abc import Iterable
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)

def absolute_submodule_path(submodule, cur_dir=inspect.stack()[0][1]):
    """
    Returns the absolute path of the inputted SnD submodule based on an inputted
    absolute path, or the absolute path of this file.

    Parameters
    ----------
    submodule : str or Path
        Desired submodule path.

    cur_dir : str or Path, optional
        Absolute path to use as a template for the full submodule path.

    Returns
    -------
    full_path : str
        Full string path to the inputted submodule.
    """
    dir_parts = Path(cur_dir).parts
    sub_parts = Path(submodule).parts
    base_path = Path(*dir_parts[:dir_parts.index(sub_parts[0])])
    if str(base_path) == ".":
        logger.warning("Could not match base path with desired submodule.")
    full_path = base_path / Path(submodule)
    return str(full_path)

LOG_DIR = absolute_submodule_path("HXRSnD/logs")

def get_logger(name, stream_level=logging.INFO, log_file=True, 
               log_dir=Path("."), max_bytes=10*1024*1024):
    """
    Returns a properly configured logger that has a stream handler and a file
    handler. This was made so that immediately setting up both a stream and
    file handler is as easy as just calling this function and forgetting about
    the details.

    Parameters
    ----------
    name : str
        Name for the logger.

    stream_level : logging.level, optional
        Logging level for what prints to the console.

    log_file : bool, optional
        Save to a log file.

    log_dir : Path, optional
        Path to where the log file should be saved.
        
    max_bytes : int, optional
        Size of the log file in bytes.

    Returns
    -------
    logger : logging.logger
        Properly configured logger that has a stream and optionally a file
        handler.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # One format to display the user and another for debugging
    format_stream = "%(message)4s"
    format_debug = "%(asctime)s:%(filename)s:%(lineno)4s - " \
      "%(funcName)s():    %(levelname)-8s %(message)4s"
    # Prevent logging from propagating to the root logger
    logger.propagate = 0

    # Setup the stream logger
    console = logging.StreamHandler()
    console.setLevel(stream_level)

    # Print log messages nicely if we arent in debug mode
    if stream_level >= logging.INFO:
        stream_formatter = logging.Formatter(format_stream)
    else:
        stream_formatter = logging.Formatter(format_debug)
    console.setFormatter(stream_formatter)
    logger.addHandler(console)
    
    # Log to a file
    if log_file:
        log_file = log_dir / "log.txt"

        # Create the inputted foler if it doesnt already exist
        if not log_dir.exists():
            log_dir.mkdir(parents=True)
        # Create the file if it doesnt already exist
        if not log_file.exists():
            log_file.touch()

        # Setup the file handler
        file_handler = RotatingFileHandler(
            str(log_file), mode='a', maxBytes=max_bytes, backupCount=2,
            encoding=None, delay=0)
        file_formatter = logging.Formatter(format_debug)
        file_handler.setFormatter(file_formatter)

        # Always save everything
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

    return logger

logger = get_logger(__name__)

def isiterable(obj):
    """
    Function that determines if an object is an iterable, not including 
    str.

    Parameters
    ----------
    obj : object
        Object to test if it is an iterable.

    Returns
    -------
    bool : bool
        True if the obj is an iterable, False if not.
    """
    if isinstance(obj, str):
        return False
    else:
        return isinstance(obj, Iterable)

def _flatten(inp_iter):
    """
    Recursively iterate through values in nested iterables.

    Parameters
    ----------
    inp_iter : iterable
        The iterable to flatten.

    Returns
    -------
    value : object
        The contents of the iterable
    """
    for val in inp_iter:
        if isiterable(val):
            for ival in _flatten(val):
                yield ival
        else:
            yield val
            
def flatten(inp_iter):
    """
    Returns a flattened list of the inputted iterable.

    Parameters
    ----------
    inp_iter : iterable
        The iterable to flatten.

    Returns
    -------
    flattened_iter : list
        The contents of the iterable as a flat list
    """
    return list(_flatten(inp_iter))
