#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# # # # # # # # # # # # # # # # # # # # # #
# Ilya Mazlov # https://github.com/wi1k1n #
# # # # # # # # # # # # # # # # # # # # # #

# The original script is from:
# 		Author: Aerandir14
# 		Source: https://www.instructables.com/PWM-Regulated-Fan-Based-on-CPU-Temperature-for-Ras/

import RPi.GPIO as GPIO
import time, sys, datetime as dt, math

def tryParseInt(v):
    try:
        ret = int(v)
    except:
        return None
    return ret

def between(v, lb=None, ub=None):
    if lb is None and ub is None:
        return True
    if lb is None:
        return v <= ub
    if ub is None:
        return v >= lb
    return v >= lb and v <= ub
# def between(v, lb, ub):
#     return min(ub, max(lb, v))

def wrongArgsExit():
    print('Wrong arguments. Run script with: fan_pin: int, fan_min_speed: int, fan_pwm: int')
    sys.exit()

def getThresholdState(thresholds, curval):
    for i, v in enumerate(thresholds):
        if curval < v:
            return i
    return len(thresholds)

def valWithinHysteresis(thresholds, curThreshold, hyst, val):
    if curThreshold == 0:
        ret = between(val, thresholds[0] - hyst, thresholds[0])
        print(' | w/hyst-0: {0}'.format(ret), end='')
        return ret
    if curThreshold == len(thresholds):
        ret = between(val, thresholds[-1], thresholds[-1] + hyst)
        print(' | w/hyst-l: {0}'.format(ret), end='')
        return ret
    ret = between(val, thresholds[curThreshold] - hyst, thresholds[curThreshold]) \
        or between(val, thresholds[curThreshold - 1], thresholds[curThreshold - 1] + hyst)
    print(' | w/hyst-b: {0}'.format(ret), end='')
    return ret

def valsHysteresis(thresholds, curThreshold, hyst, val):
    if curThreshold == len(thresholds):
        return (thresholds[-1] - hyst, math.inf)
    mx = thresholds[curThreshold] + hyst
    mn = thresholds[curThreshold - 1] - hyst
    return (mn, mx) if mn <= mx else (-math.inf, mx)

def getSpeedForTempThreshold(tempThresholds, speedThresholds, curTempThreshold):
    if curTempThreshold == 0:
        return 0
    if curTempThreshold == len(tempThresholds):
        return 100
    return speedThresholds[curTempThreshold - 1]

def readTemperature():
    # with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
    with open('/home/pi/tmp/temp', 'r') as f:
        temp = float(f.read())
    return temp


if __name__ == '__main__':
    print('Welcome to Fanctl script!')

    # Configuration
    WAIT_TIME = 1  # [s] Time to wait between each refresh
    HYSTERESIS = 1  # [°C] Fan speed will change only of the difference of temperature is higher than hysteresis
    # MIN_CYCLE_DURATION = 3  # [s] Minimum time which need to pass within the same state between temp thresholds
    TEMP_THRESHOLDS = [50, 55, 65, 70]  # [°C]
    SPEED_THRESHOLDS = [0, 30, 70, 100]  # [%]

    if len(sys.argv) < 4:
        wrongArgsExit()
    
    fanPin = tryParseInt(sys.argv[1])  # GPIO.BCM pin
    fanMinSpeed = tryParseInt(sys.argv[2])  # [%]
    fanPWM = tryParseInt(sys.argv[3])  # [Hz]

    if any([v is None for v in [fanPin, fanMinSpeed, fanPWM]]) or not between(fanMinSpeed, 0, 100) or not between(fanPWM, 1):
        wrongArgsExit()

    print('FAN_PIN:', fanPin)
    print('MIN_SPEED:', fanMinSpeed)
    print('PWM_FREQ:', fanPWM)

    # Setup GPIO pin
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(fanPin, GPIO.OUT, initial=GPIO.LOW)
    fan = GPIO.PWM(fanPin, fanPWM)
    fan.start(0)

    if not len(TEMP_THRESHOLDS) or not len(SPEED_THRESHOLDS) or len(TEMP_THRESHOLDS) != len(SPEED_THRESHOLDS):
        print("Wrong thredsholds. There should be at least one threshold. Temp thresholds should contain the same number of thresholds as in speed thresholds.")
        sys.exit()

    temp = readTemperature()
    print('[Init] Temp: {0}'.format(temp), end='')
    lastThresholdState = getThresholdState(TEMP_THRESHOLDS, temp)
    print(' | ind: {0}'.format(lastThresholdState), end='')
    newSpeed = getSpeedForTempThreshold(TEMP_THRESHOLDS, SPEED_THRESHOLDS, lastThresholdState)
    fan.ChangeDutyCycle(newSpeed)
    print(' | change -> {0}'.format(newSpeed))

    try:
        while 1:
            temp = readTemperature()
            print('Temp: {0}'.format(temp), end='')

            curThresholdState = getThresholdState(TEMP_THRESHOLDS, temp)
            print(' | ind: {0}'.format(curThresholdState), end='')

            if curThresholdState > lastThresholdState:
                lastThresholdState = curThresholdState
                newSpeed = getSpeedForTempThreshold(TEMP_THRESHOLDS, SPEED_THRESHOLDS, lastThresholdState)
                fan.ChangeDutyCycle(newSpeed)
                print(' | change -> {0}'.format(newSpeed), end='')
            elif lastThresholdState - curThresholdState > 1:
                lastThresholdState = curThresholdState + 1
                newSpeed = getSpeedForTempThreshold(TEMP_THRESHOLDS, SPEED_THRESHOLDS, lastThresholdState)
                fan.ChangeDutyCycle(newSpeed)
                print(' | change -> {0}'.format(newSpeed), end='')

            print()
            time.sleep(WAIT_TIME)

    except KeyboardInterrupt:
        print("Fan ctrl interrupted by keyboard")
        GPIO.cleanup()
        sys.exit()


    i = 0
    cpuTemp = 0
    fanSpeed = 0
    cpuTempOld = 0
    fanSpeedOld = 0

    try:
        while 1:
            # Read CPU temperature
            cpuTempFile = open("/sys/class/thermal/thermal_zone0/temp", "r")
            cpuTemp = float(cpuTempFile.read()) / 1000
            cpuTempFile.close()

            # Calculate desired fan speed
            if abs(cpuTemp - cpuTempOld) > hyst:
                # Below first value, fan will run at min speed.
                if cpuTemp < tempSteps[0]:
                    fanSpeed = speedSteps[0]
                # Above last value, fan will run at max speed
                elif cpuTemp >= tempSteps[len(tempSteps) - 1]:
                    fanSpeed = speedSteps[len(tempSteps) - 1]
                # If temperature is between 2 steps, fan speed is calculated by linear interpolation
                else:
                    for i in range(0, len(tempSteps) - 1):
                        if (cpuTemp >= tempSteps[i]) and (cpuTemp < tempSteps[i + 1]):
                            fanSpeed = round((speedSteps[i + 1] - speedSteps[i])
                                             / (tempSteps[i + 1] - tempSteps[i])
                                             * (cpuTemp - tempSteps[i])
                                             + speedSteps[i], 1)

                if fanSpeed != fanSpeedOld:
                    if (fanSpeed != fanSpeedOld
                            and (fanSpeed >= fanMinSpeed or fanSpeed == 0)):
                        fan.ChangeDutyCycle(fanSpeed)
                        fanSpeedOld = fanSpeed
                cpuTempOld = cpuTemp
            
            # print('Temp: ', cpuTemp, 'Fan: ', fanSpeed, 'Freq: ', fanPWM)
            # Wait until next refresh
            time.sleep(WAIT_TIME)


    # If a keyboard interrupt occurs (ctrl + c), the GPIO is set to 0 and the program exits.
    except KeyboardInterrupt:
        print("Fan ctrl interrupted by keyboard")
        GPIO.cleanup()
        sys.exit()
