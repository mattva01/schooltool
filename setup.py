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

import sys
if sys.version_info < (2, 3):
    print >> sys.stderr, '%s: need Python 2.3 or later' % sys.argv[0]
    print >> sys.stderr, 'your python is %s' % sys.version
    sys.exit(1)

from distutils.core import setup, Extension

ext_modules = [Extension("zope.interface._zope_interface_ospec",
                         ["src/zope/interface/_zope_interface_ospec.c"])]

setup(name="schooltool",
      version="0.0.1pre",
      package_dir={'': 'src'},
      ext_modules=ext_modules)
