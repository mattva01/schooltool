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
Utilities for debugging SchoolTool
"""

import logging
from persistence.list import PersistentList
from zope.interface import implements, Attribute
from schooltool.membership import MemberMixin
from schooltool.interfaces import IEventTarget

__metaclass__ = type

class IEventLog(IEventTarget):
    """Event log that stores all received events persistently"""

    received = Attribute("""List of received events""")

    def clear():
        """Clear received events list"""


class EventLog(MemberMixin):

    implements(IEventLog)

    def __init__(self):
        MemberMixin.__init__(self)
        self.received = PersistentList()

    def notify(self, event):
        self.received.append(event)

    def clear(self):
        del self.received[:]


class EventLogger(MemberMixin):

    implements(IEventTarget)

    def notify(self, event):
        logging.debug('Event: %r' % event)

