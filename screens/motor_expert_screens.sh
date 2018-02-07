# Expert screen launcher.
# Launches the screens for both the attocube and aerotech motors from the most
# recently released versions of their respective IOCs. Decides which screen to
# launch based on the motor name passed in the second argument. For example, if
# the aerotech motor screen is desired, pass the base PV as the first argument,
# and "aerotech" as the second argument.

# # # Source the epics env
# # source /reg/g/pcds/setup/epicsenv-cur.sh
# Commenting the above lines out so that people know this was done at one point,
# but undone. Sourcing epicsenv-cur cannot happen after entering the conda env
# otherwise some shared libraries do not load properly.

# If "aerotech" is passed as the second argument, load the aerotech screens
if [ "$2" == "aerotech" ]; then
    # Change directories to the most recent release of ioc/common/aerotech
    cd $(ls -td /reg/g/pcds/package/epics/3.14/ioc/common/aerotech/*/motorScreens | head -1)
    edm -x -eolc -m "MOTOR=${1}" ens_main.edl >& /dev/null &

# If "attocube" is passed as the second argument, load attocube screens
elif [ "$2" == "attocube" ]; then
    # Change directories to the most recent release of ioc/common/ecc100
    cd $(ls -td /reg/g/pcds/package/epics/3.14/ioc/common/ecc100/*/motorScreens | head -1)
    edm -x -eolc -m "PV=${1}" eccStepModule.edl >& /dev/null &
fi
