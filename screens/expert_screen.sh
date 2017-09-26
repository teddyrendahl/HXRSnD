# Source the epics env
source /reg/g/pcds/setup/epicsenv-cur.sh

# If one argument is provided, load the aerotech screens
if [ "$#" -eq 1 ]; then
    cd /reg/neh/home4/mcbrowne/trunk2/ioc/common/aerotech/current/motorScreens
    edm -x -eolc -m "MOTOR=${1}" ens_main.edl >& /dev/null &

# If two arguments are provided, load attocube screens
elif [ "$#" -eq 2 ]; then
    cd /reg/g/pcds/package/epics/3.14/ioc/common/ecc100/R1.0.1/data
    edm -x -eolc -m "P=${1},axis=${2}" eccStepModule.edl >& /dev/null &
fi
