#!/bin/bash
#
# run-import.sh
#
# A wrapper script for schoolbell-import.py (which should be in the same
# directory).
#
# For this script to work you need a number of things:
#
# 1- You should have already run run-export.sh
# 2- You need an installation of SchoolBell-1.0 that has *not* been run yet.
#    (If you already started the instance, just remove the Data.fs and wave
#    goodbye to anything you added to it)
# 3- The ability to edit this script.
#
#
# Edit this script
#
# 1- Add colon-separated paths to your SchoolBell 1.0 python libs and the
#    Zope3 libs that came with it to the PYTHONPATH variable here.  If you are
#    using a fresh download, this would be something like:
#
#    PYTHONPATH="/path/to/schoolbell-1.0/src:/path/to/schoolbell-1.0/Zope3/src"

PYTHONPATH=

# 2- Set the NEWDB variable to point to the new database you want to create
#    (Data.fs)
#
#    OLDDB="Data.fs"

NEWDB=

# 3- If you needed to change DUMPDIR in run-export.sh, make the same change
#    here.

DUMPDIR="/var/schooltool"

# 4- If you need to use a specific python binary, set it here
#

PYTHON=/usr/bin/python2.3

# 5- Run the script:
#
#    $ ./run-import.sh
#
#    And wait.... when it exits (assuming you saw no nasty tracebacks) your
#    database will have been imported!
#
#    Now, you're not done yet.  Wherever the new Data.fs was created (in this
#    directory by default) you need to move it to where SchoolBell-1.0 will
#    expect to find it.
#
#    For Ubuntu/Debian installations, this is /var/lib/schoolbell/Data.fs
#


##############################################################################
# No touchie below here.
#

INFILE="schoolbell-export.xml"

export PYTHONPATH

${PYTHON} schoolbell-import.py $NEWDB ${DUMPDIR}/$INFILE ${DUMPDIR}/calendars
