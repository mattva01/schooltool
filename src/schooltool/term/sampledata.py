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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""Term sample data generation
"""
import datetime
import zope.interface

from schooltool.term.interfaces import ITermContainer
from schooltool.term import term
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.schoolyear import SchoolYear
from schooltool.sampledata.interfaces import ISampleDataPlugin

class SampleTerms(object):
    """Sample data generator for terms."""
    zope.interface.implements(ISampleDataPlugin)

    name = 'terms'
    dependencies = ()

    def generate(self, app, seed=None):
        date = datetime.date

        syc = ISchoolYearContainer(app)
        syc['2005-2006'] = SchoolYear("2005-2006",
                                      date(2005, 8, 22),
                                      date(2006, 12, 22))

        fall = term.Term('2005-fall', date(2005, 8, 22), date(2005, 12, 23))
        fall.addWeekdays(0, 1, 2, 3, 4)
        terms = ITermContainer(app)
        terms['2005-fall'] = fall

        spring = term.Term('2006-spring', date(2006, 1, 26), date(2006, 5, 31))
        spring.addWeekdays(0, 1, 2, 3, 4)
        terms['2006-spring'] = spring

        fall = term.Term('2006-fall', date(2006, 8, 21), date(2006, 12, 22))
        fall.addWeekdays(0, 1, 2, 3, 4)
        terms['2006-fall'] = fall
