#!/usr/bin/env python2.3
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
    import re
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

from distutils.core import setup, Extension

# Set up dependencies for the BTrees package
base_btrees_depends = [
    "Zope3/src/persistent/cPersistence.h",
    "Zope3/src/BTrees/BTreeItemsTemplate.c",
    "Zope3/src/BTrees/BTreeModuleTemplate.c",
    "Zope3/src/BTrees/BTreeTemplate.c",
    "Zope3/src/BTrees/BucketTemplate.c",
    "Zope3/src/BTrees/MergeTemplate.c",
    "Zope3/src/BTrees/SetOpTemplate.c",
    "Zope3/src/BTrees/SetTemplate.c",
    "Zope3/src/BTrees/TreeSetTemplate.c",
    "Zope3/src/BTrees/sorters.c",
    ]

_flavors = {"O": "object", "I": "int"}

KEY_H = "Zope3/src/BTrees/%skeymacros.h"
VALUE_H = "Zope3/src/BTrees/%svaluemacros.h"

include_dirs = ['src']


def BTreeExtension(flavor):
    key = flavor[0]
    value = flavor[1]
    name = "BTrees._%sBTree" % flavor
    sources = ["Zope3/src/BTrees/_%sBTree.c" % flavor]
    kwargs = {"include_dirs": ['Zope3/src/persistent']}
    if flavor != "fs":
        kwargs["depends"] = (base_btrees_depends + [KEY_H % _flavors[key],
                                                    VALUE_H % _flavors[value]])
    return Extension(name, sources, **kwargs)


ext_modules = [
    BTreeExtension("OO"),
    BTreeExtension("IO"),
    BTreeExtension("OI"),
    BTreeExtension("II"),
    BTreeExtension("fs"),
    Extension(name = 'persistent.cPersistence',
              include_dirs = ['Zope3/src/persistent'],
              sources= ['Zope3/src/persistent/cPersistence.c',
                        'Zope3/src/persistent/ring.c'],
              depends = ['Zope3/src/persistent/cPersistence.h',
                         'Zope3/src/persistent/ring.h',
                         'Zope3/src/persistent/ring.c']
              ),
    Extension(name = 'persistent.cPickleCache',
              include_dirs = ['Zope3/src/persistent'],
              sources= ['Zope3/src/persistent/cPickleCache.c',
                        'Zope3/src/persistent/ring.c'],
               depends = ['Zope3/src/persistent/cPersistence.h',
                         'Zope3/src/persistent/ring.h',
                         'Zope3/src/persistent/ring.c']
              ),
    Extension(name = 'persistent.TimeStamp',
              include_dirs = ['Zope3/src/persistent'],
              sources= ['Zope3/src/persistent/TimeStamp.c']
              ),
    Extension(name = 'ZODB.winlock',
              include_dirs = ['Zope3/src/persistent'],
              sources = ['Zope3/src/ZODB/winlock.c']
              ),
    Extension("zope.interface._zope_interface_coptimizations",
              ["Zope3/src/zope/interface/_zope_interface_coptimizations.c"]),
]

setup(name="schooltool",
      version="0.9",
      package_dir={'': 'Zope3/src'},
      ext_modules=ext_modules)
