#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
Adapter subscriber
"""
from zope.interface import Interface
from zope.interface import implements
from zope.component.interfaces import IObjectEvent
from zope.component import adapter
from zope.component import adapts
from zope.component import getAdapters

from schooltool.schoolyear.interfaces import ISubscriber

@adapter(Interface)
def subscriberAdapterDispatcher(event):
    subscribers = getAdapters((event,), ISubscriber)
    for name, subscriber in subscribers:
        subscriber()


class EventAdapterSubscriber(object):
    implements(ISubscriber)

    def __init__(self, event):
        self.event = event

    def __call__(self):
        raise NotImplementedError("Please override this method in subclasses")


class ObjectEventAdapterSubscriberDispatcher(EventAdapterSubscriber):
    adapts(IObjectEvent)
    implements(ISubscriber)

    def __call__(self):
        subscribers = getAdapters((self.event, self.event.object), ISubscriber)
        for name, subscriber in subscribers:
            subscriber()


class ObjectEventAdapterSubscriber(object):
    implements(ISubscriber)

    def __init__(self, event, object):
        self.event = event
        self.object = object

    def __call__(self):
        raise NotImplementedError("Please override this method in subclasses")
