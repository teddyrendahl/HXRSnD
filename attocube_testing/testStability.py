#! /reg/g/pcds/pkg_mgr/release/controls-0.1.8/x86_64-rhel6-gcc44-opt/bin/python

from attocube_test_script import testStability as testStability
from attocube_test_script import home as home
from common.motor import Motor as psmotor
import sys
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

if len(sys.argv) == 2:
    index = int(sys.argv[1])
    data = testStability(motors[index])
if len(sys.argv) == 3:
    index = int(sys.argv[1])
    t = float(sys.argv[2])
    data = testStability(motors[index], t)

home(motors[index])

datafile = open('stability_results.csv', 'wb')
writer = csv.writer(datafile)
writer.writerow(['Stability Test'])
writer.writerow(data)
