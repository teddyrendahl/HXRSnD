# Expert screen launcher.
# Launches the screens for both the attocube and aerotech motors from the most
# recently released versions of their respective IOCs. Decides which screen to
# launch based on the number of parameters passed.

# To use for aerotech motors, simply pass the PV for the motor. For attocube
# motors, pass the base PV and axis.

# # # Source the epics env
# # source /reg/g/pcds/setup/epicsenv-cur.sh
# Commenting the above lines out so that people know this was done at one point,
# but undone. Sourcing epicsenv-cur cannot happen after entering the conda env
# otherwise some shared libraries do not load properly.

# If one argument is provided, load the aerotech screens
if [ "$#" -eq 1 ]; then
    # Change directories to the most recent release of ioc/common/aerotech
    cd $(ls -td /reg/g/pcds/package/epics/3.14/ioc/common/aerotech/*/motorScreens | head -1)
    edm -x -eolc -m "MOTOR=${1}" ens_main.edl >& /dev/null &

# If two arguments are provided, load attocube screens
elif [ "$#" -eq 2 ]; then
    # Change directories to the most recent release of ioc/common/ecc100    
    cd $(ls -td /reg/g/pcds/package/epics/3.14/ioc/common/ecc100/*/data | head -1)
    edm -x -eolc -m "P=${1},axis=${2}" eccStepModule.edl >& /dev/null &
fi
