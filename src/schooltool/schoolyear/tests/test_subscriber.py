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
"""Unit tests for schooltool.schoolyear.subscriber
"""
import unittest
import doctest

from zope.component.interfaces import ObjectEvent
from zope.component.interfaces import IObjectEvent
from zope.component import provideAdapter
from zope.component import adapts
from zope.interface import implements
from zope.interface import Interface
from zope.app.testing import setup

from schooltool.schoolyear.interfaces import ISubscriber
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriberDispatcher
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.schoolyear.subscriber import subscriberAdapterDispatcher


def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def doctest_subscriberAdapterDispatcher():
    """Tests for a subscriber that delegates it's work to adapters.

    subscriberAdapterDispatcher delegates handling of the event to
    subscribers.

    Subscribers are named adapters that adapt events to ISubscriber.

    If there are no subscribers registered, nothing happens:

        >>> class IEvent(Interface):
        ...     "Marker interface for an event."

        >>> class Event(object):
        ...     implements(IEvent)
        ...     def __init__(self, id):
        ...         self.id = id
        ...     def __repr__(self):
        ...         return "<Event %s>" % self.id
        ...     __str__ = __repr__

        >>> event = Event("1")
        >>> subscriberAdapterDispatcher(event)

    Let's register a subscriber:

        >>> results = []
        >>> class SimpleHandler(object):
        ...     adapts(IEvent)
        ...     implements(ISubscriber)
        ...     def __init__(self, event):
        ...         self.event = event
        ...     def __call__(self):
        ...         results.append("Did stuff on %s" % self.event)
        >>> provideAdapter(SimpleHandler, name="Handler1")

    And run the dispatcher again:

        >>> subscriberAdapterDispatcher(event)
        >>> results
        ['Did stuff on <Event 1>']

    We can have another subscriber registered with a different name too:

        >>> class AnotherHandler(SimpleHandler):
        ...     def __call__(self):
        ...         results.append("Did more stuff on %s" % self.event)
        >>> provideAdapter(AnotherHandler, name="Handler2")

        >>> results = []
        >>> subscriberAdapterDispatcher(event)
        >>> sorted(results)
        ['Did more stuff on <Event 1>', 'Did stuff on <Event 1>']

    """


def doctest_ObjectEventAdapterSubscriberDispatcher():
    """Tests for an event dispatcher that picks object specific adapter subscribers.

    With object events we want to be able to register subscribers for
    specific event/object pairs, instead of just events:

        >>> results = []
        >>> class SimpleAddedSubscriber(ObjectEventAdapterSubscriber):
        ...     adapts(IObjectEvent, Interface)
        ...     def __call__(self):
        ...        results.append("<Did stuff on %s (event %s)>" % (self.object,
        ...                                                         self.event))
        >>> provideAdapter(SimpleAddedSubscriber, name="simple")

    As our subscriber is registered for any type of an object we will
    get it called for any kind of object event:

        >>> event = ObjectEvent("<a string>")
        >>> ObjectEventAdapterSubscriberDispatcher(event)()
        >>> results
        ['<Did stuff on <a string> (event <...ObjectEvent object at ...>)>']

    If there are 2 adapters with the same name, the more specific one
    will get picked though:

        >>> class IAmAnObject(Interface):
        ...    "A marker interface for a test"

        >>> class SpecificObject(object):
        ...     implements(IAmAnObject)

        >>> class SpecificAddedSubscriber(ObjectEventAdapterSubscriber):
        ...     adapts(IObjectEvent, IAmAnObject)
        ...     def __call__(self):
        ...        results.append("<Did specific stuff on %s (event %s)>" % (self.object,
        ...                                                                  self.event))
        >>> provideAdapter(SpecificAddedSubscriber, name="simple")

        >>> results = []
        >>> event = ObjectEvent(SpecificObject())
        >>> ObjectEventAdapterSubscriberDispatcher(event)()
        >>> results
        ['<Did specific stuff on <...SpecificObject object at ...>
                          (event <...ObjectEvent object at ...>)>']


    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                             optionflags=doctest.ELLIPSIS
                                       | doctest.NORMALIZE_WHITESPACE),
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
