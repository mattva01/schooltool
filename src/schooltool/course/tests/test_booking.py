#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
Unit tests for course and section implementations.

$Id$
"""


import unittest
from zope.testing import doctest
from zope.interface.verify import verifyObject
from schooltool.timetable.tests.test_source import BaseTimetableSourceTest


class TestBookingTimetableSource(BaseTimetableSourceTest, unittest.TestCase):

    def createAdapter(self, context):
        from schooltool.course.booking import BookingTimetableSource
        return BookingTimetableSource(context)

    def createRelationship(self, context, related):
        from schooltool.course.booking import SectionBooking
        SectionBooking(section=related, resource=context)



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBookingTimetableSource))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
