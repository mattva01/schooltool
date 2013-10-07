#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Functional Testing Utilities for export/import
"""
import os

from schooltool.testing.functional import ZCMLLayer


dir = os.path.abspath(os.path.dirname(__file__))
filename = os.path.join(dir, 'ftesting.zcml')

export_functional_layer = ZCMLLayer(filename,
                                    __name__,
                                    'export_functional_layer')
