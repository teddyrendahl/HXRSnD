#! /reg/g/pcds/pkg_mgr/release/controls-0.1.8/x86_64-rhel6-gcc44-opt/bin/python

from common.motor import Motor as psmotor
import time
import psp.Pv as Pv
import csv


# Read in attocubes to be tested and build lists of PVs
stages = []
with open('stages.txt', 'rb') as f:
    reader = csv.reader(f)
    for row in reader:
        stages.append(row[0].strip())

# Define motors
motors = []
for stage in enumerate(stages):
    motors.append(psmotor(stage[1], 'acube%i' % stage[0]))


# Define functions used in testing

def wait(stage, timeout=5):
    waitTime = 0
    while stage.ismoving and waitTime < timeout:
        time.sleep(0.1)
        waitTime += 0.1

    
def testRepeatability(stage):
    # Move repeatably between different positions, with increasing step size.
    
    # List of positions to move between
    positions = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.00,
                200.0, 500.0, 1000.0, 2000.0, 5000.0]
    # Initialize data array
    data = []

    # Loop over position pairs
    for i in range(len(positions)-1):
        pos1 = positions[i]
        pos2 = positions[i+1]
        diffs = []
        # Average 10 identical moves
        for j in range(10):
            print 'Move %i' % j
            if j == 0:
                stage.mv(pos1)
                print 'Moving to position 1 ... '
                wait(stage, 3) 
            start = stage.wm()
            stage.mv(pos2)
            print 'Moving to position 2 ... '
            wait(stage, 3) 
            stage.mv(pos1)
            print 'Moving back to position 1 ... '
            wait(stage, 3) 
            end = stage.wm()
            diff = end - start
            diffs.append(diff)
        averageDiff = sum(diffs)/(len(diffs)+1)
        step = pos2 - pos1
        run = step, diffs, averageDiff
        data.append(run)
   
    #Send home after all moves are complete and return data
    stage.mv(0.0)
    wait(stage, 3)
    return data


def testStability(stage):
    # Monitor the position of the stage for a set amount of time

    f = 1.0 # frequency of measurements in hertz
    t = 60.0 # time to measure in seconds
    data = []
    elapsed = 0.0
    print 'Testing stability, please wait ... '
    while elapsed < t:
        data.append(stage.wm())
        time.sleep(1.0/f)
        if elapsed % (t/10.0) == 0 and elapsed != 0.0:
            print 'Stability test is %d%% done, please wait ... ' % ((elapsed/t)*100)
        elapsed += float(1.0/f)
    print 'Stability test for stage %s is complete.' % str(stage).split('@')[0].strip()
    
    return data


def home(stage):
    # Home the stage by moving to one side, moving past the center to trip the
    # encoder reference, and then move to center.
    
    # Define homing error class
    class HomingError(Exception):
        '''Raise this when homing fails.'''

    print 'Homing ... '    
    origLowLim = stage.get_lowlim()
    stage.set_lowlim(-16000.0) # Set low lim very low, allowing the following move
    limits = stage.check_limit_switches()
    if limits[0] == 'low':
        pass # Don't move if already at limit for some reason
    else:
        stage.mv(-15000.0) # Move the stage very far, forcing it to hit a limit
        wait(stage, 10)

    # If stage has hit low limit, move to 1 degree to pass center reference
    if stage.check_limit_switches()[0] == 'low':
        stage.mv(1000.0)
        wait(stage, 5)
    else:
        raise HomingError('Lower limit never reached.')
    
    # Reset limit, move to center
    stage.set_lowlim(origLowLim) 
    stage.mv(0.0)
    wait(stage, 5)
    print 'Homing complete.'


def testAccuracy(stage, step):
    # Move stage in small increments across its entire range, to measure accuracy
   
    # Home the motor, and then move to lower limit switch
    home(stage) 
    origLowLim = stage.get_lowlim()
    stage.set_lowlim(-16000.0) # Set low lim very low, allowing the following move
    stage.mv(-15000.0) # Move the stage very far, forcing it to hit a limit
    wait(stage, 5)
    data = []
    moves = []

    # Move up in specified increments, allowing autocolimator to measure distance, until 
    # high limit switch is hit    
    while stage.check_limit_switches()[0] != 'high':
        currPos = stage.wm()
        movePos = currPos + step
        moves.append(movePos)
        stage.mv(movePos)
        wait(stage, 1)
        data.append(stage.wm())
    
    # Reset the stage to its original settings and move to center
    stage.set_lowlim(origLowLim) 
    stage.mv(0.0)
    wait(stage, 3)

    return moves, data

    
### Begin testing ###
if __name__ == '__main__':

    startTime = time.time()

    # Create a file that results will be written to
    datafile = open('results.csv', 'wb')
    writer = csv.writer(datafile)

    # Home the stage(s) initially
    for motor in enumerate(motors):
        home(motors[motor[0]])

    # Test repeatability, i.e. move to a position, move somewhere else, move back,
    # check the difference.
    # for motor in enumerate(motors):
        repeatability = testRepeatability(motor[1])
        writer.writerow(['attocube stage %i' % motor[0]])
        writer.writerows([['Repeatability Test']])
        for run in enumerate(repeatability):
            data = [['Run %i' % run[0]], ['step', run[1][0]], ['Differences'], run[1][1], ['Difference Average', run[1][2]]]
            writer.writerows(data)
        writer.writerow(['']) # Append a blank line to separate sections

    # Test the stability of the position by measuring position over a period of time
    # for motor in enumerate(motors):
        stability = testStability(motor[1])
        writer.writerow(['attocube stage %i' % motor[0]])
        writer.writerows([['Stability Test']])
        writer.writerows([stability])
        writer.writerow(['']) # Append a blank line to separate sections

    # Test the accuracy of the stage by moving in small increments, recoddring the
    # set position and the readback position for later comparison with external 
    # measurement.
    for motor in enumerate(motors):
        moves, data = testAccuracy(motor[1], 100.0)
        moves.insert(0, 'Move Positions')
        data.insert(0, 'Position Readbacks')
        writer.writerow(['Accuracy Test'])
        writer.writerows([moves, data])
        writer.writerow(['']) # Append a blank line to separate sections

    endTime = time.time()

    # Calculate the elapsed time
    timeDiff = endTime - startTime
    m, s = divmod(timeDiff, 60)
    h, m = divmod(m, 60)
    print 'Time elapsed: %d hours, %02d minutes, %02d seconds' % (h, m, s)
