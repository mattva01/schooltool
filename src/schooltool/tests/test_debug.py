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


class TestEventLog(unittest.TestCase):

    def test(self):
        from schooltool.debug import EventLog, IEventLog
        from schooltool.interfaces import IEventTarget
        event_log = EventLog()
        verifyObject(IEventTarget, event_log)
        verifyObject(IEventLog, event_log)
        event1, event2 = object(), object()
        event_log.notify(event1)
        event_log.notify(event2)
        self.assertEquals(event_log.received, [event1, event2])

        event_log.clear()
        self.assertEquals(event_log.received, [])


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
        from schooltool.debug import EventLogger
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
    suite.addTest(unittest.makeSuite(TestEventLogger))
    return suite

if __name__ == '__main__':
    unittest.main()
