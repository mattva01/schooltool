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
from schooltool.translation import _
from schooltool.clients import csvclient

if os.path.exists('Data.fs'):
    print _("Please remove Data.fs before creating a sample school")
    sys.exit(1)

for file in ('groups.csv',  'teachers.csv', 'pupils.csv'):
    if not os.path.exists(file):
        print "%s not found." %  file
        print (_("Please create the sample data files by running "
               "src/schooltool/clients/datagen.py"))
        sys.exit(1)


print _("Starting server...")
pid = os.spawnlp(os.P_NOWAIT, "python2.3",
                 "SchoolTool", os.path.abspath("src/schooltool/main.py"))
try:
    rest = 0.2
    while True:
        try:
            urllib.urlopen("http://localhost:7001/")
        except IOError:
            time.sleep(rest)
            if rest > 4:
                print _("Problems starting the server")
                sys.exit(1)
            rest *= 2
        else:
            print
            break

    print _("Importing data...")
    csvclient.main()
    print _("Creating a timetable...")
    os.system("make runclient < ttconfig.data")
finally:
    print _("Stopping the server...")
    os.kill(pid, 15)

print _("Done.")

