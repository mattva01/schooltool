#!/usr/bin/env python2.3
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005    Shuttleworth Foundation,
#                       Brian Sutherland
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
SchoolTool setup script.
"""

#
# Check requisite version numbers
#

import sys
import os
import re

if sys.version_info < (2, 3):
    print >> sys.stderr, '%s: need Python 2.3 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)

try:
    import twisted.copyright
except ImportError:
    print >> sys.stderr, ("%s: apparently you do not have Twisted installed."
                          % sys.argv[0])
    print >> sys.stderr, "You will not be able to run the SchoolTool server."
    print >> sys.stderr
else:
    m = re.match(r"(\d+)[.](\d+)[.](\d+)(?:[a-z]+\d*)?$",
                 twisted.copyright.version)
    if not m:
        print >> sys.stderr, ("%s: you have Twisted version %s."
                              % (sys.argv[0], twisted.copyright.version))
        print >> sys.stderr, ("I was unable to parse the version number."
                              "  You will not be able to run")
        print >> sys.stderr, ("the SchoolTool server if this version is"
                              " older than 1.3.0.")
        print >> sys.stderr
    else:
        ver = tuple(map(int, m.groups()))
        if ver < (1, 3, 0):
            print >> sys.stderr, ("%s: you have Twisted version %s."
                                  % (sys.argv[0], twisted.copyright.version))
            print >> sys.stderr, ("You need at least version 1.3.0 in order to"
                                  " be able to run the SchoolTool")
            print >> sys.stderr, "server."
            print >> sys.stderr


#
# Do the setup
#

from distutils.core import setup

# which package are we setting up
if sys.argv[1] == 'schooltool':
    package = 'schooltool'
    sys.argv[1:2] = []
elif sys.argv[1] == 'schoolbell':
    package = 'schoolbell'
    sys.argv[1:2] = []
else:
    print >> sys.stderr, ("You must specify the package to build as the first"
                        " command line option, either schooltool or schoolbell")
    sys.exit(1)

# Set a default manifest
if sys.argv[1] == 'sdist':
    sys.argv[2:2] = ['-t', 'MANIFEST.in.' + package,
            '-m', 'MANIFEST.' + package]

# regex for finding data files
datafile_re = re.compile('.*\.(pt|js|png|css|mo|rng|xml|pot)\Z')

# TODO: ask distutils to build Zope 3 extension modules somehow
if package == 'schooltool':
    # find the data files
    data_files = []
    os.chdir('src')
    for root, dirs, files in os.walk('schooltool'):
        tmp = [os.path.join('src', root, file) for file in files \
                if datafile_re.match(file, 1)]
        if tmp:
            data_files.append((root, tmp))
    os.chdir('..')
    # Setup SchoolTool
    setup(name="schooltool",
        version="0.10rc1",
        url='http://www.schooltool.org',
        package_dir={'': 'src'},
        packages=['schooltool', 'schooltool.interfaces',
            'schooltool.schema', 'schooltool.translation',
            'schooltool.rest', 'schooltool.browser',
            'schooltool.clients'],
        data_files=[('sampleschool', ['persons.csv', 'groups.csv',
                'resources.csv', 'timetable.csv', 'ttconfig.data'])]
            + data_files,
        scripts=['scripts/import-sampleschool', 'scripts/schooltool',
            'scripts/schooltool-client'])
elif package == 'schoolbell':
    # find the data files
    data_files = []
    os.chdir('src')
    for root, dirs, files in os.walk('schoolbell'):
        tmp = [os.path.join('src', root, file) for file in files \
                if datafile_re.match(file, 1)]
        if tmp:
            data_files.append((root, tmp))
    os.chdir('..')
    # Setup SchoolBell
    setup(name="schoolbell",
        version="1.0rc1",
        url='http://www.schooltool.org/schoolbell',
        package_dir={'': 'src'},
        packages=['schoolbell', 'schoolbell.relationship',
            'schoolbell.calendar', 'schoolbell.app', 'schoolbell.app.browser'],
        data_files=data_files,
        scripts=['scripts/schoolbell'])
