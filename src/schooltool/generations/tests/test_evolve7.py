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
Unit tests for schooltool.generations.evolve6

$Id$
"""

import unittest
from datetime import date, time, timedelta
from pprint import pprint

from zope.app.testing import setup
from zope.testing import doctest
from zope.app.container.btree import BTreeContainer

from schooltool.generations.tests import ContextStub
import schooltool.app # Dead chicken to avoid issue 390
from schooltool.testing import setup as stsetup

from schooltool.timetable import SchooldayTemplate, SchooldaySlot
from schooltool.timetable.model import SequentialDaysTimetableModel
from schooltool.timetable.schema import TimetableSchema, TimetableSchemaDay


def setUp(test):
    setup.placelessSetUp()
    setup.setUpAnnotations()
    stsetup.setupTimetabling()


def tearDown(test):
    setup.placelessTearDown()


def doctest_evolve7_convert_exceptions():
    """Evolution to generation 7.

        >>> context = ContextStub()
        >>> app = {'ttschemas': BTreeContainer()}
        >>> context.root_folder['app'] = app

    Suppose we have a timetable schema with a model that has exception days:

        >>> day_templates = {None: SchooldayTemplate()}
        >>> model = SequentialDaysTimetableModel(('A', 'B'), day_templates)
        >>> schema = TimetableSchema(('A', 'B'), model=model)
        >>> app['ttschemas']['example'] = schema
        >>> ex = model.exceptionDays[date(2005, 10, 14)] = SchooldayTemplate()
        >>> p1 = SchooldaySlot(time(8, 0), timedelta(minutes=55))
        >>> p2 = SchooldaySlot(time(9, 0), timedelta(minutes=55))
        >>> p3 = SchooldaySlot(time(10, 0), timedelta(minutes=55))
        >>> p4 = SchooldaySlot(time(11, 0), timedelta(minutes=55))

        >>> ex.add(p1)
        >>> ex.add(p2)
        >>> ex.add(p3)
        >>> ex.add(p4)

    The slots are in fact old SchooldayPeriod instances, and they have
    title attributes on them.

        >>> p1.title = 'alpha'
        >>> p2.title = 'beta'
        >>> p3.title = 'gamma'
        >>> p4.title = 'delta'

    We call the evolution script:

        >>> from schooltool.generations.evolve7 import evolve
        >>> evolve(context)

    Let's inspect the model exceptions:

        >>> len(model.exceptionDays)
        1

    We see a list of tuples (period, slot).  They are sorted in the
    chronological order.

        >>> pprint(model.exceptionDays[date(2005, 10, 14)])
        [('alpha', <schooltool.timetable.SchooldaySlot ...>),
         ('beta', <schooltool.timetable.SchooldaySlot ...>),
         ('gamma', <schooltool.timetable.SchooldaySlot ...>),
         ('delta', <schooltool.timetable.SchooldaySlot ...>)]

        >>> for period, slot in model.exceptionDays[date(2005, 10, 14)]:
        ...     print period.ljust(5), slot.tstart, slot.duration
        alpha 08:00:00 0:55:00
        beta  09:00:00 0:55:00
        gamma 10:00:00 0:55:00
        delta 11:00:00 0:55:00

    """


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
