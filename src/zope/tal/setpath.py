##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Read a module search path from .path file.

If .path file isn't found in the directory of the setpath.py module, then try
to import ZODB.  If that succeeds, we assume the path is already set up
correctly.  If that import fails, an IOError is raised.

$Id$
"""

# TODO: Why does this want to find ZODB ???

import os
import sys

dir = os.path.dirname(__file__)
path = os.path.join(dir, ".path")
try:
    f = open(path)
except IOError:
    try:
        # If we can import ZODB, our sys.path is set up well enough already
        import ZODB
    except ImportError:
        raise IOError("Can't find ZODB package.  Please edit %s to point to "
                      "your Zope's lib/python directory" % path)
else:
    for line in f.readlines():
        line = line.strip()
        if line and line[0] != '#':
            for dir in line.split(os.pathsep):
                dir = os.path.expanduser(os.path.expandvars(dir))
                if dir not in sys.path:
                    sys.path.append(dir)
        # Must import this first to initialize Persistence properly
        import ZODB
