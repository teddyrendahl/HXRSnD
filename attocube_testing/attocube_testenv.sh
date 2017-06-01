#! /bin/bash

# Set enviroment variables necessary to test attocube stage
source /reg/g/pcds/setup/pathmunge.sh

PYTHONPATH=
LD_LIBRARY_PATH=


export EPICS_CA_MAX_ARRAY_BYTES=8000000
export PSPKG_ROOT=/reg/g/pcds/pkg_mgr

export PSPKG_RELEASE="mec-3.0.0"
source $PSPKG_ROOT/etc/set_env.sh
