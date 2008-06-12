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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Unit tests for schooltool.generations.evolve27
"""
import unittest

from zope.app.testing import setup
from zope.testing import doctest
from zope.interface import implements

from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication


class SectionStub(object):

    def __init__(self, name):
        self.__name__ = name

    def __repr__(self):
        return self.__name__


class TimetableStub(object):

    def __init__(self, name):
        self.__name__ = name


class AppStub(dict):
    implements(ISchoolToolApplication)

    def __init__(self):
        self['sections'] = {}
        for name in ['section1', 'section2', 'section3',
                     'section4', 'section5', 'section6']:
            self['sections'][name] = SectionStub(name)
        self['terms'] = {}
        self['terms']['term1'] = "Term 1"
        self['terms']['term2'] = "Term 2"
        self['ttschemas'] = {}
        self['ttschemas']['schema1'] = "Schema 1"
        self['ttschemas']['schema2'] = "Schema 2"


def doctest_evolve12():
    """Evolution to generation 27.

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()

        >>> s2 = app['sections']['section2']
        >>> s2.__annotations__ = {}

        >>> tt_dicts = []
        >>> for section_id in ['section3', 'section4', 'section5', 'section6']:
        ...     section = app['sections'][section_id]
        ...     tt_dict = {}
        ...     tt_dicts.append(tt_dict)
        ...     section.__annotations__ = {'schooltool.timetable.timetables': tt_dict}

        >>> tt_dicts[1]['term1.schema1'] = TimetableStub('term1.schema1')
        >>> tt_dicts[2]['term1.schema2'] = TimetableStub('term1.schema2')
        >>> tt_dicts[3]['term1.schema2'] = TimetableStub('term1.schema2')
        >>> tt_dicts[3]['term2.schema2'] = TimetableStub('term2.schema2')
        >>> tt_dicts[3]['term1.schema1'] = TimetableStub('term1.schema1')

        >>> from schooltool.generations.evolve27 import evolve
        >>> evolve(context)

    As we can see ids were properly mapped to appropriate term and
    school timetable:

        >>> for section_id, section in sorted(app['sections'].items()):
        ...     print "Timetables for section %s" % section
        ...     ttdict = getattr(section, '__annotations__', {}).get(
        ...                'schooltool.timetable.timetables', {})
        ...     if not ttdict:
        ...         print "  No timetables"
        ...     for key, timetable in sorted(ttdict.items()):
        ...         print "  %s -> (term = %s, schooltt = %s)" % (key, timetable.term, timetable.schooltt)
        Timetables for section section1
          No timetables
        Timetables for section section2
          No timetables
        Timetables for section section3
          No timetables
        Timetables for section section4
          term1.schema1 -> (term = Term 1, schooltt = Schema 1)
        Timetables for section section5
          term1.schema2 -> (term = Term 1, schooltt = Schema 2)
        Timetables for section section6
          term1.schema1 -> (term = Term 1, schooltt = Schema 1)
          term1.schema2 -> (term = Term 1, schooltt = Schema 2)
          term2.schema2 -> (term = Term 2, schooltt = Schema 2)

    """


def setUp(test):
    setup.placelessSetUp()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
