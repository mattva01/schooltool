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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
SchoolTool libraries and application
"""

_version = None

def get_version():
    global _version
    if _version is not None:
        return _version
    import os
    directory = os.path.split(__file__)[0]
    f = open(os.path.join(directory, 'version.txt'), 'r')
    result = f.read()
    _version = result
    f.close()
    return result

from zope.i18nmessageid import MessageFactory
SchoolToolMessage = MessageFactory("schooltool")
