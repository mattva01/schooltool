#!/usr/bin/env python
"""
Run the server asynchronously, then run the CSV client, and stop the server.

This script is supposed to be run from the Makefile.

$Id$
"""
import os
import sys
import time
import urllib
from schooltool import csvclient

if os.path.exists('Data.fs'):
    print "Please remove Data.fs before creating a sample school"
    sys.exit(1)

print "Starting server..."
pid = os.spawnlp(os.P_NOWAIT, "python2.3",
                 "SchoolTool", os.path.abspath("src/schooltool/main.py"))
try:
    rest = 0.2
    while True:
        try:
            urllib.urlopen("http://localhost:8080/")
        except IOError:
            time.sleep(rest)
            if rest > 4:
                print "Problems starting the server"
                sys.exit(1)
            rest *= 2
        else:
            print
            break

    print "Importing data..."
    csvclient.main()
finally:
    print "Stopping the server..."
    os.kill(pid, 15)

print "Done."

