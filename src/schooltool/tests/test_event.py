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
Unit tests for schooltool.event

$Id$
"""

import unittest
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.interfaces import IEvent

__metaclass__ = type


class TargetStub:
    events = ()

    def notify(self, event):
        self.events += (event, )


class TestEventMixin(unittest.TestCase):

    def setUp(self):
        from schooltool import event
        self.event_service = TargetStub()
        self.real_getEventService = event.getEventService
        event.getEventService = self.getEventService

    def tearDown(self):
        from schooltool import event
        event.getEventService = self.real_getEventService

    def getEventService(self, context):
        return self.event_service

    def test(self):
        from schooltool.event import EventMixin
        from schooltool.interfaces import IEvent
        e = EventMixin()
        verifyObject(IEvent, e)

    def test_dispatch(self):
        from schooltool.event import EventMixin
        target1 = TargetStub()
        target2 = TargetStub()
        e = EventMixin()
        e.dispatch(target1)
        e.dispatch(target2)
        self.assertEquals(self.event_service.events, (e, ))
        self.assertEquals(target1.events, (e, ))
        self.assertEquals(target2.events, (e, ))

    def test_dispatch_repeatedly(self):
        from schooltool.event import EventMixin
        target = TargetStub()
        e = EventMixin()
        e.dispatch(target)
        e.dispatch(target)
        e.dispatch(target)
        self.assertEquals(self.event_service.events, (e, ))
        self.assertEquals(target.events, (e, ))


class IEventA(IEvent):
    pass


class IEventB(IEvent):
    pass


class EventAStub:
    implements(IEventA)

    def __init__(self):
        self.dispatched_to = []

    def dispatch(self, target):
        self.dispatched_to.append(target)


class EventActionStub:

    def __init__(self, evtype):
        self.eventType = evtype
        self.calls = []

    def handle(self, event, target):
        self.calls.append((event, target))


class TestEventTargetMixin(unittest.TestCase):

    def test(self):
        from schooltool.event import EventTargetMixin
        from schooltool.interfaces import IEventTarget, IEventConfigurable
        et = EventTargetMixin()
        verifyObject(IEventTarget, et)
        verifyObject(IEventConfigurable, et)
        self.assertEquals(list(et.eventTable), [])

    def test_handle(self):
        from schooltool.event import EventTargetMixin
        et = EventTargetMixin()
        handler_a = EventActionStub(IEventA)
        handler_b = EventActionStub(IEventB)
        et.eventTable.extend([handler_a, handler_b])
        event = EventAStub()
        et.notify(event)
        self.assertEqual(handler_a.calls, [(event, et)])
        self.assertEqual(handler_b.calls, [])


class TestEventActionMixins(unittest.TestCase):

    def test(self):
        from schooltool.event import EventActionMixin
        from schooltool.interfaces import IEventAction
        marker = object()
        ea = EventActionMixin(marker)
        verifyObject(IEventAction, ea)
        self.assertEquals(ea.eventType, marker)
        self.assertRaises(NotImplementedError, ea.handle, None, None)

    def testCallAction(self):
        from schooltool.event import CallAction
        from schooltool.interfaces import IEventAction

        honeypot = TargetStub()
        callback = honeypot.notify
        ca = CallAction(callback)
        # XXX cannot use verifyObject here due to incorrect assumtions it makes
        #     verifyObject(ICallAction, ca)
        verifyObject(IEventAction, ca)
        self.assert_(IEventAction.providedBy(ca))

        self.assertEquals(ca.eventType, IEvent)
        self.assertEquals(ca.callback, callback)

        event = EventAStub()
        target = object()
        ca.handle(event, target)
        self.assertEquals(honeypot.events, (event, ))

    def testLookupAction(self):
        from schooltool.event import LookupAction
        from schooltool.interfaces import ILookupAction
        la = LookupAction()
        verifyObject(ILookupAction, la)
        self.assertEquals(list(la.eventTable), [])
        self.assertEquals(la.eventType, IEvent)

        handler_a = EventActionStub(IEventA)
        handler_b = EventActionStub(IEventB)
        la = LookupAction(eventType=IEventA, eventTable=[handler_a, handler_b])
        self.assertEquals(la.eventType, IEventA)
        event = EventAStub()
        target = object()
        la.handle(event, target)
        self.assertEqual(handler_a.calls, [(event, target)])
        self.assertEqual(handler_b.calls, [])

    def testRouteToMembersAction(self):
        from schooltool.event import RouteToMembersAction
        from schooltool.interfaces import IRouteToMembersAction
        from schooltool.uris import URIMember
        action = RouteToMembersAction(IEventA)
        verifyObject(IRouteToMembersAction, action)
        self.assertEquals(action.eventType, IEventA)

        event = EventAStub()
        child1, child2 = object(), object()
        target = object()

        def getRelatedObjectsStub(ob, uri):
            if target == ob and uri == URIMember:
                return [child1, child2]
            return []

        action.getRelatedObjects = getRelatedObjectsStub

        action.handle(event, target)
        dispatched_to = event.dispatched_to
        members = [child1, child2]
        members.sort()
        dispatched_to.sort()
        self.assertEquals(dispatched_to, members)

    def testRouteToGroupsAction(self):
        from schooltool.event import RouteToGroupsAction
        from schooltool.interfaces import IRouteToGroupsAction
        from schooltool.uris import URIGroup
        action = RouteToGroupsAction(IEventA)
        verifyObject(IRouteToGroupsAction, action)
        self.assertEquals(action.eventType, IEventA)

        event = EventAStub()
        group1, group2 = object(), object()
        target = object()

        def getRelatedObjectsStub(ob, uri):
            if target == ob and uri == URIGroup:
                return [group1, group2]
            return []

        action.getRelatedObjects = getRelatedObjectsStub
        action.handle(event, target)
        dispatched_to = event.dispatched_to
        groups = [group1, group2]
        groups.sort()
        dispatched_to.sort()
        self.assertEquals(dispatched_to, groups)

    def testRouteToRelationshipsAction(self):
        from schooltool.event import RouteToRelationshipsAction
        from schooltool.interfaces import IRouteToRelationshipsAction
        from schooltool.uris import ISpecificURI

        class URIFriend(ISpecificURI):
            """http://ns.example.org/role/friend"""

        class LinkStub:
            def __init__(self, friend):
                self._friend = friend
            def traverse(self):
                return self._friend

        class RelatableStub:
            def __init__(self, role, friend):
                self._role = role
                self._friend = friend
            def listLinks(self, role):
                if role == self._role:
                    return [LinkStub(self._friend)]
                else:
                    return []

        action = RouteToRelationshipsAction(URIFriend, IEventA)
        verifyObject(IRouteToRelationshipsAction, action)
        self.assertEquals(action.role, URIFriend)
        self.assertRaises(TypeError,
                          RouteToRelationshipsAction, IEventA, URIFriend)

        event = EventAStub()
        friend = object()
        target = RelatableStub(URIFriend, friend)
        action.handle(event, target)
        self.assertEquals(event.dispatched_to, [friend])


class TestEventService(unittest.TestCase):

    def test(self):
        from schooltool.event import EventService
        from schooltool.interfaces import IEventService
        es = EventService()
        verifyObject(IEventService, es)

    def test_subscribe(self):
        from schooltool.event import EventService
        es = EventService()
        target = object()
        es.subscribe(target, IEventA)
        self.assertEquals(list(es.listSubscriptions()), [(target, IEventA)])
        es.subscribe(target, IEventA)
        self.assertEquals(list(es.listSubscriptions()),
                          [(target, IEventA), (target, IEventA)])

    def test_unsubscribe(self):
        from schooltool.event import EventService
        es = EventService()
        target = object()
        es.subscribe(target, IEventA)
        es.subscribe(target, IEventA)
        self.assertRaises(ValueError, es.unsubscribe, target, IEvent)
        es.unsubscribe(target, IEventA)
        self.assertEquals(list(es.listSubscriptions()), [(target, IEventA)])
        es.unsubscribe(target, IEventA)
        self.assertEquals(list(es.listSubscriptions()), [])

    def test_unsubscribeAll(self):
        from schooltool.event import EventService
        es = EventService()
        target1 = object()
        target2 = object()
        es.subscribe(target1, IEventA)
        es.subscribe(target1, IEventB)
        es.subscribe(target2, IEvent)
        es.unsubscribeAll(target1)
        self.assertEquals(list(es.listSubscriptions()), [(target2, IEvent)])
        es.unsubscribeAll(target1)
        self.assertEquals(list(es.listSubscriptions()), [(target2, IEvent)])

    def test_notify(self):
        from schooltool.event import EventService
        es = EventService()
        target1 = TargetStub()
        target2 = TargetStub()
        es.subscribe(target1, IEventB)
        es.subscribe(target2, IEvent)
        es.subscribe(target2, IEventA)
        event = EventAStub()
        es.notify(event)
        self.assertEquals(event.dispatched_to, [target2, target2])

    def test_nonevents(self):
        from zope.interface import Interface, directlyProvides
        from schooltool.event import EventService

        class IUnrelated(Interface):
            pass

        es = EventService()
        target = TargetStub()
        es.subscribe(target, IUnrelated)
        event = EventAStub()
        directlyProvides(event, IUnrelated)
        es.notify(event)
        self.assertEquals(event.dispatched_to, [target])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEventMixin))
    suite.addTest(unittest.makeSuite(TestEventTargetMixin))
    suite.addTest(unittest.makeSuite(TestEventActionMixins))
    suite.addTest(unittest.makeSuite(TestEventService))
    return suite

if __name__ == '__main__':
    unittest.main()
