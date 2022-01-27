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

def wrongArgsExit():
    print('Wrong arguments. Run script with: fan_pin: int, fan_min_speed: int, fan_pwm: int')
    sys.exit()

def getThresholdState(thresholds, curval):
    for i, v in enumerate(thresholds):
        if curval < v:
            return i
    return len(thresholds)

def getSpeedForTempThreshold(tempThresholds, speedThresholds, curTempThreshold):
    if curTempThreshold == 0:
        return 0
    if curTempThreshold == len(tempThresholds):
        return 100
    return speedThresholds[curTempThreshold - 1]

def readTemperature():
    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
        temp = float(f.read()) * 1e-3
    return temp

def setFanSpeed(tThresholds, sThresholds, state):
    newSpeed = getSpeedForTempThreshold(tThresholds, sThresholds, state)
    print('Set speed to {0}%'.format(newSpeed))
    fan.ChangeDutyCycle(newSpeed)


if __name__ == '__main__':
    print('Welcome to Fanctl script!')

    # Configuration
    WAIT_TIME = 2  # [s] Time to wait between each refresh
    TEMP_THRESHOLDS = [50, 55, 65]  # [°C]
    SPEED_THRESHOLDS = [0, 50, 100]  # [%]

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
    lastThresholdState = getThresholdState(TEMP_THRESHOLDS, temp)
    setFanSpeed(TEMP_THRESHOLDS, SPEED_THRESHOLDS, lastThresholdState)

    try:
        while 1:
            temp = readTemperature()
            curThresholdState = getThresholdState(TEMP_THRESHOLDS, temp)

            if curThresholdState > lastThresholdState:
                lastThresholdState = curThresholdState
                print('Temp: {0} | '.format(temp), end='')
                setFanSpeed(TEMP_THRESHOLDS, SPEED_THRESHOLDS, lastThresholdState)
            elif lastThresholdState - curThresholdState > 1:
                lastThresholdState = curThresholdState + 1
                print('Temp: {0} | '.format(temp), end='')
                setFanSpeed(TEMP_THRESHOLDS, SPEED_THRESHOLDS, lastThresholdState)
            time.sleep(WAIT_TIME)

    except KeyboardInterrupt:
        print("Fan ctrl interrupted by keyboard")
        GPIO.cleanup()
        sys.exit()