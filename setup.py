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
    m = re.match(r"(\d+)[.](\d+)[.](\d+)$", twisted.copyright.version)
    if not m:
        print >> sys.stderr, ("%s: you have Twisted version %s."
                              % (sys.argv[0], twisted.copyright.version))
        print >> sys.stderr, ("I was unable to parse the version number."
                              "  You will not be able to run")
        print >> sys.stderr, ("the SchoolTool server if this version is"
                              " older than 1.1.0.")
        print >> sys.stderr
    else:
        ver = tuple(map(int, m.groups()))
        if ver < (1, 1, 0):
            print >> sys.stderr, ("%s: you have Twisted version %s."
                                  % (sys.argv[0], twisted.copyright.version))
            print >> sys.stderr, ("You need at least version 1.1.0 in order to"
                                  " be able to run the SchoolTool")
            print >> sys.stderr, "server."
            print >> sys.stderr


#
# Do the setup
#

from distutils.core import setup, Extension

base_btrees_depends = [
    "src/persistence/persistence.h",
    "src/persistence/persistenceAPI.h",
    "src/zodb/btrees/BTreeItemsTemplate.c",
    "src/zodb/btrees/BTreeModuleTemplate.c",
    "src/zodb/btrees/BTreeTemplate.c",
    "src/zodb/btrees/BucketTemplate.c",
    "src/zodb/btrees/MergeTemplate.c",
    "src/zodb/btrees/SetOpTemplate.c",
    "src/zodb/btrees/SetTemplate.c",
    "src/zodb/btrees/TreeSetTemplate.c",
    "src/zodb/btrees/sorters.c",
]

ext_modules = [

    # zope.interface

    Extension("zope.interface._zope_interface_ospec",
              ["src/zope/interface/_zope_interface_ospec.c"]),

    # persistence

    Extension("persistence._persistence",
              ["src/persistence/persistence.c"],
              depends=["src/persistence/persistence.h",
                       "src/persistence/persistenceAPI.h"]),

    # zodb

    Extension("zodb._timestamp",
              ["src/zodb/_timestamp.c"]),
    Extension("zodb.storage._helper",
              ["src/zodb/storage/_helper.c"]),
    Extension("zodb.btrees._zodb_btrees_fsBTree",
              ["src/zodb/btrees/_zodb_btrees_fsBTree.c"],
              include_dirs=["src"],
              depends=base_btrees_depends),
    Extension("zodb.btrees._zodb_btrees_OOBTree",
              ["src/zodb/btrees/_zodb_btrees_OOBTree.c"],
              include_dirs=["src"],
              depends=base_btrees_depends + ["src/zodb/btrees/objectkeymacros.h",
                                             "src/zodb/btrees/objectvaluemacros.h"]),
    Extension("zodb.btrees._zodb_btrees_OIBTree",
              ["src/zodb/btrees/_zodb_btrees_OIBTree.c"],
              include_dirs=["src"],
              depends=base_btrees_depends + ["src/zodb/btrees/objectkeymacros.h",
                                             "src/zodb/btrees/intvaluemacros.h"]),
    Extension("zodb.btrees._zodb_btrees_IOBTree",
              ["src/zodb/btrees/_zodb_btrees_IOBTree.c"],
              include_dirs=["src"],
              depends=base_btrees_depends + ["src/zodb/btrees/intkeymacros.h",
                                             "src/zodb/btrees/objectvaluemacros.h"]),
    Extension("zodb.btrees._zodb_btrees_IIBTree",
              ["src/zodb/btrees/_zodb_btrees_IIBTree.c"],
              include_dirs=["src"],
              depends=base_btrees_depends + ["src/zodb/btrees/intkeymacros.h",
                                             "src/zodb/btrees/intvaluemacros.h"]),

]

if sys.platform == "win32":
    ext_modules.append(Extension("zodb.winlock", ["src/zodb/winlock.c"]))


setup(name="schooltool",
      version="0.0.1pre",
      package_dir={'': 'src'},
      ext_modules=ext_modules)
