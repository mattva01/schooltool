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
Unit tests for the schooltool package.
"""

import unittest
import logging
from zope.interface.verify import verifyObject

__metaclass__ = type


class DateTimeStub:

    step = 10
    start = 100 - step

    def utcnow(self):
        self.start += self.step
        return self.start


class TestEventLog(unittest.TestCase):

    def test(self):
        from schooltool.eventlog import EventLog, IEventLog
        from schooltool.interfaces import IEventTarget
        event_log = EventLog()
        event_log.datetime_hook = DateTimeStub()
        verifyObject(IEventTarget, event_log)
        verifyObject(IEventLog, event_log)
        event1, event2 = object(), object()
        event_log.notify(event1)
        event_log.notify(event2)
        self.assertEquals(list(event_log.getReceived()),
                          [(100, event1), (110, event2)])

        event_log.clear()
        self.assertEquals(list(event_log.getReceived()), [])

        event_log.enabled = False
        event_log.notify(event1)
        self.assertEquals(list(event_log.getReceived()), [])


class TestEventLogUtility(unittest.TestCase):

    def test(self):
        from schooltool.eventlog import EventLogUtility, IEventLogUtility
        event_log = EventLogUtility()
        verifyObject(IEventLogUtility, event_log)


class TestEventLogFacet(unittest.TestCase):

    def test(self):
        from schooltool.eventlog import EventLogFacet, IEventLogFacet
        from schooltool.interfaces import IEvent, ICallAction

        event_log = EventLogFacet()
        verifyObject(IEventLogFacet, event_log)

        self.assertEquals(len(event_log.eventTable), 1)
        ea = event_log.eventTable[0]
        self.assert_(ICallAction.providedBy(ea))
        self.assertEquals(ea.eventType, IEvent)
        self.assertEquals(ea.callback, event_log.notify)


class TestEventLogger(unittest.TestCase):

    def setUp(self):

        class LogHandler(logging.Handler):
            def __init__(self):
                logging.Handler.__init__(self)
                self.emitted = []

            def emit(self, record):
                self.emitted.append(self.format(record))

        self.log_handler = LogHandler()
        self.old_handlers = logging.root.handlers
        logging.root.handlers = []
        logging.root.addHandler(self.log_handler)
        self.old_level = logging.root.level
        logging.root.setLevel(logging.DEBUG)

    def tearDown(self):
        logging.root.removeHandler(self.log_handler)
        logging.root.handlers = self.old_handlers
        logging.root.setLevel(self.old_level)

    def test(self):
        from schooltool.eventlog import EventLogger
        from schooltool.interfaces import IEventTarget
        event_logger = EventLogger()
        verifyObject(IEventTarget, event_logger)

        class EventStub:
            def __init__(self, name):
                self.name = name

            def __repr__(self):
                return '<%s>' % self.name

        event1 = EventStub('event1')
        event_logger.notify(event1)
        event2 = EventStub('event2')
        event_logger.notify(event2)

        self.assertEquals(self.log_handler.emitted,
                          ['Event: <event1>', 'Event: <event2>'])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEventLog))
    suite.addTest(unittest.makeSuite(TestEventLogUtility))
    suite.addTest(unittest.makeSuite(TestEventLogFacet))
    suite.addTest(unittest.makeSuite(TestEventLogger))
    return suite

if __name__ == '__main__':
    unittest.main()
