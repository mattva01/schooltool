#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Functional Testing Utilities for resource.
"""
import os

from schooltool.testing.functional import ZCMLLayer

dir = os.path.abspath(os.path.dirname(__file__))
filename = os.path.join(dir, 'ftesting.zcml')

resource_functional_layer = ZCMLLayer(filename,
                                      __name__,
                                      'resource_functional_layer')
