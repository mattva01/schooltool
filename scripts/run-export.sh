#!/bin/bash
#
# run-export.sh
#
# A wrapper script for schoolbell-export.py (which should be in the same
# directory).
#
# For this script to work, you need a number of things:
#
# 1- A SchoolBell 0.8 or 0.9 database (Data.fs)
# 2- Python libraries that come with SchoolBell 0.8 or 0.9 .If you no longer
#    have the libraries installed see the next section for instructions.
# 3- The ability to edit this script.
# 
# 
# If 0.8/0.9 Has Been Removed
#
# 1- Goto http://www.schooltool.org/releases/0.9/ and download a release.
# 2- Unpack the release somewhere safe:
#
#    $ tar xvfz schooltool-0.9.tar.gz
#    $ cd schooltool-0.9
#    $ make
#
# 3- Remember where this is.
#
# 
# Edit this script:
#
# 1- Add colon-separated paths to your SchoolBell 0.8/0.9 python libs and the
#    Zope3 libs that came with it to the PYTHONPATH variable here.  If you are
#    using a fresh download, this would be something like:
#
#    PYTHONPATH="/path/to/schooltool-0.9/src:/path/to/schooltool-0.9/Zope3/src"

PYTHONPATH=

# 2- Set the OLDDB variable to point to your old database (Data.fs).
# FIXME By default, where is this?
#    OLDDB="/var/lib/schooltool/Data.fs"

OLDDB=

# 3- In some situations you may need to edit this setting.  It controls where
#    the data from the database is dumped on the filesystem.  Usually leaving
#    it alone is fine unless you don't have write permissions to /tmp.
#
#    NOTE: if you change this here, remember to make the same change to
#          run-import.sh

DUMPDIR="/var/schooltool"

# 4- If you need to use a specific python binary, set it here
#

PYTHON=/usr/bin/python2.3

# 5- Run the script:
#
#    $ ./run-export.sh
#
#    And wait.... when it exits (assuming you saw no nasty tracebacks) your
#    database will have been exported!
#
#    Now move on to run-import.sh and get your data imported into 1.0



##############################################################################
# No touchie below here.
#

OUTFILE="schoolbell-export.xml"

mkdir -p $DUMPDIR
mkdir -p $DUMPDIR/calendars

export PYTHONPATH

${PYTHON} schoolbell-export.py $OLDDB ${DUMPDIR}/$OUTFILE ${DUMPDIR}/calendars
