#!/usr/bin/python

# code by Albert Zeyer, www.az2000.de
# 2012-06-14

import os, os.path, sys
mydir = os.path.dirname(__file__) or os.getcwd()
mydir = os.path.abspath(mydir)
sys.path += [mydir + "/../common"]

import better_exchook
better_exchook.install()

import datetime, time
import ast, subprocess
import re
import binstruct
from appinfo import *

localDev = binstruct.Dict()

import easycfg
easycfg.setup(userdir + "/client.cfg", globals(), ["localDev"])

if not localDev:
	pubCryptKey,privCryptKey = binstruct.genkeypair()
	pubSignKey,privSignKey = binstruct.genkeypair()
	localDev.publicKeys = binstruct.Dict({"crypt": pubCryptKey, "sign": pubSignKey})
	localDev.privateKeys = binstruct.Dict({"crypt": privCryptKey, "sign": privSignKey})
	easycfg.save()
localDev.type = "RemoteControlClient"
localDev.appInfo = {"appId":appid, "version":version}

import fscomm
fscomm.setup(appid, localDev)

localDev = fscomm.registerDev(localDev)

def pushDataFile(fn):
	# TODO check change-time if needed...
	serverDev.storeData(localDev, fn, open(mydir + "/../pydata/" + fn).read())
	
def execRemotePy(conn, pythonCmd):
	conn.sendPackage(pythonCmd)
	print "sent %r, waiting..." % pythonCmd
	while True:
		for p in conn.readPackages():
			print "got", repr(p), "from", conn.dstDev
			return p
		try: time.sleep(0.5)
		except: sys.exit(1)

def main(arg):
	global serverDev
	serverDev = None
	for d in fscomm.devices():
		if d.type != "RemoteControlServer": continue
		print "found server:", d
		serverDev = d
	
	pushDataFile("media_keys.py")
	conn = serverDev.connectFrom(localDev, {"intent":"PythonExec.1"})
	
	pyCmd = "eval(compile(" + \
		"dstDev.loadData(srcDev, 'media_keys.py') + " + \
		"'\\n\\nHIDPostAuxKey(NX_KEYTYPE_%s)'" % arg.upper() + \
		", '<>', 'exec'))"
	p = execRemotePy(conn, pyCmd)
	if "ret" in p["data"]: print "success!"
	else: print "failure"
	
	conn.close()
	print "finished"
	
if __name__ == '__main__':
	pythonCmd = sys.argv[1] if len(sys.argv) > 1 else "''.join(map(chr,range(97,100)))"
	main(pythonCmd)
	