#! /reg/g/pcds/pkg_mgr/release/controls-0.1.8/x86_64-rhel6-gcc44-opt/bin/python

from attocube_test_script import testRepeatability as testRepeatability
from attocube_test_script import home as home
from common.motor import Motor as psmotor
import sys
from sys import exit
import csv

# Read in attocubes to be tested and build lists of PVs
stages = []
with open('stages.txt', 'rb') as f:
    reader = csv.reader(f)
    for row in reader:
        stages.append(row[0].strip())

# Define motors and run script
motors = []
for stage in enumerate(stages):
    motors.append(psmotor(stage[1], 'acube%i' % stage[0]))

args = sys.argv
if len(args) >= 3:
    index = int(sys.argv[1])
    positions = [float(x) for x in sys.argv[2:]]
    repeat = testRepeatability(motors[index], positions)
if len(args) == 2:
    index = int(sys.argv[1])
    repeat = testRepeatability(motors[index])

datafile = open('repeatability_resulst.csv', 'wb')
writer = csv.writer(datafile)
writer.writerow(['Repeatability Test'])
for run in repeat:
    data = [['step', run[0]], ['Differences'], run[1], ['Difference Average', run[2]]]
    writer.writerows(data)
