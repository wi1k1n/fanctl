#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# # # # # # # # # # # # # # # # # # # # # #
# Ilya Mazlov # https://github.com/wi1k1n #
# # # # # # # # # # # # # # # # # # # # # #

import time, sys, os, os.path as op, getpass, subprocess

def is_root():
    return os.geteuid() == 0

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
    if callBack(*args, **kwargs):
        print('\t\t..done')
    else:
        print('\t\t..failed')
        sys.exit()


def createServiceLink():
    systemServiceLink = op.abspath('/etc/systemd/system/fanctl.service')
    if op.isfile(systemServiceLink):
        inp = input('\t> File {0} already exists. Overwrite? [yN]: '.format(systemServiceLink))
        if inp.lower() != 'y':
            sys.exit()
        tryRunFunc(os.remove, systemServiceLink)
        # tryRunFunc(subprocess.check_output, 'sudo rm {0}'.format(systemServiceLink))
    return tryRunFunc(os.symlink, op.abspath(op.join(os.getcwd(), 'fanctl.service')), systemServiceLink)

def enableService():
    return tryRunFunc(subprocess.check_output, 'systemctl enable fanctl.service', shell=True)
def restartService():
    return tryRunFunc(subprocess.check_output, 'systemctl restart fanctl.service', shell=True)

if __name__ == '__main__':
	if not is_root():
		print('Please run with sudo!')
		sys.exit()
	runFuncOrExit('> Creating link to fanctl.service..', createServiceLink)
	runFuncOrExit('> Enabling fanctl.service..', enableService)
	runFuncOrExit('> Starting fanctl.service..', restartService)