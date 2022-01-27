#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# # # # # # # # # # # # # # # # # # # # # #
# Ilya Mazlov # https://github.com/wi1k1n #
# # # # # # # # # # # # # # # # # # # # # #

# The original script is from:
#       Author: Aerandir14
#       Source: https://www.instructables.com/PWM-Regulated-Fan-Based-on-CPU-Temperature-for-Ras/

import RPi.GPIO as GPIO
import time, sys, os, os.path as op, getpass, subprocess

def is_root():
    return os.geteuid() == 0

def tryParseInt(v):
    try:
        ret = int(v)
    except:
        return None
    return ret

def tryRunFunc(callBack, *args, **kwargs):
    try:
        callBack(*args, **kwargs)
    except Exception as e:
        print('\t> Exception: {0}'.format(e))
        return False
    return True

def runFuncOrExit(printMsg, callBack, *args, **kwargs):
    if len(printMsg):
        print(printMsg)
    if callBack():
        print('\t\t..done')
    else:
        print('\t\t..failed')
        sys.exit()

def generateService():
    if op.isfile('fanctl.service'):
        inp = input('\t> File {0} already exists. Overwrite? [yN]: '.format(op.abspath('fanctl.service')))
        if inp.lower() != 'y':
            sys.exit()
    def createServiceFile():
        with open('fanctl.service', 'w') as file:
            file.write("""\
[Unit]
Description=PWM Fan Control

[Service]
Type=simple
User={username}
ExecStart=/usr/bin/python3 {scriptpath}
Restart=always

[Install]
WantedBy=default.target
""".format(username=getpass.getuser(), scriptpath=op.abspath(op.join(os.getcwd(), 'fanctl.py'))))
    return tryRunFunc(createServiceFile)

def createServiceLink():
    systemServiceLink = op.abspath('/etc/systemd/system/fanctl.service')
    if op.isfile(systemServiceLink):
        inp = input('\t> File {0} already exists. Overwrite? [yN]: '.format(systemServiceLink))
        if inp.lower() != 'y':
            sys.exit()
        tryRunFunc(os.remove, systemServiceLink)
    return tryRunFunc(os.symlink, op.abspath(op.join(os.getcwd(), 'fanctl.service')), systemServiceLink)

def enableService():
    return tryRunFunc(subprocess.check_output, 'systemctl enable fanctl.service', shell=True)
def restartService():
    return tryRunFunc(subprocess.check_output, 'systemctl restart fanctl.service', shell=True)


if __name__ == '__main__':
    print('Welcome to Fanctl calibration and install script!')
    root = True
    if not is_root():
        print('> [NO SUDO] Please check that you run this script with sudo if you want to install it to your system later!')
        root = False

    fanPin = None
    pwmFreq = 200

    # TODO: Load values from fanctl.service if possible

    # Fan GPIO pin
    if len(sys.argv) > 1:
        fanPin = tryParseInt(sys.argv[1])
        if fanPin is None:
            print('WARNING: Provided an invalid fan GPIO pin: {0}'.format(sys.argv[1]))
    
    if fanPin is None:
        print('Enter the fan pin number:')
        while 1:
            inp = input('Fan pin: ')
            if inp.lower() == 'x':
                sys.exit()
            fanPin = tryParseInt(inp)
            if fanPin is None:
                print('WARNING: Entered invalid fan GPIO pin: {0}'.format(inp))
            else:
                break;
    print('Running fan on GPIO: {0}'.format(fanPin))

    # PWM value
    if len(sys.argv) > 2:
        pwmFreq = tryParseInt(sys.argv[2])
        if fanPin is None:
            print('WARNING: Provided an invalid PWM value: {0}'.format(sys.argv[2]))
    print('Using PWM value: {0}'.format(pwmFreq))
    print()

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(fanPin, GPIO.OUT, initial=GPIO.LOW)
    fan = GPIO.PWM(fanPin, pwmFreq)
    fan.start(0);


    # Minimum spinning value
    print('>>> First calibrate minimum starting speed of your fan. Find the minimum value (between 0 and 100) when the fan reliebly does not stop spinning. Enter Y when ready.')
    while 1:
        inp = input('Fan Speed: ')
        if inp.lower() == 'y':
            break
        if inp.lower() == '':
            continue

        fanSpeed = tryParseInt(inp)
        if fanSpeed is None or fanSpeed < 0 or fanSpeed > 100:
            print('WARNING: invalid speed value: {0}. Must be an integer between 0 and 100.'.format(inp))
            continue

        if fanSpeed > 0:
            fan.ChangeDutyCycle(100)
        time.sleep(0.1)
        fan.ChangeDutyCycle(fanSpeed)
    minFanSpeed = fanSpeed
    print('Captured minimum spinning value: {0}'.format(minFanSpeed))


    # Most quiet frequency
    print('>>> Next find the most quiet frequency. Try different values bigger than 0. Current value: {0}. Enter Y when ready. Enter A to automatically run fan from minimum to maximum speed.'.format(pwmFreq))
    while 1:
        inp = input('Fan Freq: ')
        if inp.lower() == 'y':
            break
        if inp.lower() == '':
            continue
        if inp.lower() == 'a':
            print('> Auto run..')
            duration = 5
            tstep = duration / (100 - minFanSpeed)
            for i in range(minFanSpeed, 100):
                fan.ChangeDutyCycle(i)
                time.sleep(tstep)
            print('..finished!')
            fan.ChangeDutyCycle(minFanSpeed)
            continue

        pwmFreq = tryParseInt(inp)
        if pwmFreq is None or pwmFreq < 0:
            print('WARNING: invalid frequency value: {0}. Must be an integer greater than 0.'.format(inp))
            continue

        fan.stop();
        fan.ChangeFrequency(100)
        fan.start(100);
        time.sleep(0.1)
        fan.ChangeDutyCycle(minFanSpeed)
    print('Captured minimum spinning value: {0}'.format(fanSpeed))



    # Install fanctl as service
    inp = input('>>> Do you want to install Fanctl as a service? [yN]: ')
    if inp.lower() == 'y':
        if not root:
            print('> Please rerun this script with sudo!')
            sys.exit()

        print('> Current dir: {0}'.format(os.getcwd()))

        runFuncOrExit('> Generating fanctl.service..', generateService)
        runFuncOrExit('> Creating link to fanctl.service..', createServiceLink)
        runFuncOrExit('> Enabling fanctl.service..', enableService)
        runFuncOrExit('> Starting fanctl.service..', restartService)

    GPIO.cleanup()
    sys.exit()