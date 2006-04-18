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
Unit tests for schooltool.generations.evolve12

$Id$
"""

import unittest
import itertools

from zope.app.testing import setup
from zope.testing import doctest
from zope.interface import implements
from zope.component import adapts, provideAdapter
from zope.app.container.ordered import OrderedContainer

from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.attendance.interfaces import IUnresolvedAbsenceCache
from schooltool.attendance.interfaces import IHomeroomAttendance
from schooltool.attendance.interfaces import ISectionAttendance


class StudentStub(object):

    def __init__(self, name):
        self.__name__ = name
        self._section_attendance = []
        self._homeroom_attendance = []

    def __repr__(self):
        return self.__name__


class AppStub(dict):
    implements(ISchoolToolApplication)

    def __init__(self):
        # Real app has a simple unordered container, but we do not
        # want to depend on dictionary internal order in our tests
        self['persons'] = OrderedContainer()
        for name in ['s1', 's2', 's3']:
            self['persons'][name] = StudentStub(name)


class UnresolvedAbsenceCacheStub(object):
    adapts(AppStub)
    implements(IUnresolvedAbsenceCache)

    def __init__(self, app):
        self.app = app

    def add(self, student, ar):
        print "cache.add(%r, %r)" % (student, ar)


class HomeroomAttendanceStub(object):
    adapts(StudentStub)
    implements(IHomeroomAttendance)

    def __init__(self, student):
        self.student = student

    def __iter__(self):
        return itertools.imap(AttendanceLoggingProxyStub,
                              self.student._homeroom_attendance)


class SectionAttendanceStub(object):
    adapts(StudentStub)
    implements(ISectionAttendance)

    def __init__(self, student):
        self.student = student

    def __iter__(self):
        return itertools.imap(AttendanceLoggingProxyStub,
                              self.student._section_attendance)


class AttendanceRecordStub(object):
    def __init__(self, absent=False, tardy=False, explained=False):
        assert not (absent and tardy)
        self.isAbsent = lambda: absent
        self.isTardy = lambda: tardy
        self.isExplained = lambda: explained

    def __repr__(self):
        if self.isAbsent():
            what = 'absent'
        elif self.isTardy():
            what = 'tardy'
        else:
            what = 'neither'
        if self.isExplained():
            what += ' and explained'
        return what


class AttendanceLoggingProxyStub(object):
    def __init__(self, ar):
        self.attendance_record = ar
    def __getattr__(self, name):
        return getattr(self.attendance_record, name)


def doctest_evolve12():
    """Evolution to generation 12.

        >>> provideAdapter(UnresolvedAbsenceCacheStub)
        >>> provideAdapter(HomeroomAttendanceStub)
        >>> provideAdapter(SectionAttendanceStub)

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()

        >>> s1 = app['persons']['s1']
        >>> s1._section_attendance = [
        ...     AttendanceRecordStub(),
        ...     AttendanceRecordStub(absent=True),
        ...     AttendanceRecordStub(tardy=True),
        ...     AttendanceRecordStub(absent=True, explained=True),
        ...     AttendanceRecordStub(tardy=True, explained=True),
        ... ]
        >>> s2 = app['persons']['s2']
        >>> s2._homeroom_attendance = [
        ...     AttendanceRecordStub(),
        ...     AttendanceRecordStub(absent=True),
        ...     AttendanceRecordStub(tardy=True),
        ...     AttendanceRecordStub(absent=True, explained=True),
        ...     AttendanceRecordStub(tardy=True, explained=True),
        ... ]

        >>> from schooltool.generations.evolve12 import evolve
        >>> evolve(context)
        cache.add(s1, absent)
        cache.add(s1, tardy)
        cache.add(s2, absent)
        cache.add(s2, tardy)

    """


def setUp(test):
    setup.placelessSetUp()
    setup.setUpAnnotations()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
