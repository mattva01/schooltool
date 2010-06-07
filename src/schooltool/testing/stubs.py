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
Basic stubs for testing SchoolTool.
"""

from persistent.interfaces import IPersistent

from zope.interface import implements
from zope.component import adapts
from zope.keyreference.interfaces import IKeyReference


class KeyReferenceStub(object):
    implements(IKeyReference)
    adapts(IPersistent)

    key_type_id = 'schooltool.testing.stubs.KeyReferenceStub'

    def __init__(self, obj):
        self.object = obj
        self.uid = id(obj)

    def __call__(self):
        return self.object

    def __hash__(self):
        return hash(self.uid)

    def __cmp__(self, other):
        if self.key_type_id != other.key_type_id:
            return cmp(self.key_type_id, other.key_type_id)
        return cmp(self.uid, other.uid)
