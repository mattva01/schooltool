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
Term implementation

$Id$
"""
import persistent
import pytz
from datetime import datetime

import zope.interface
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.container import contained, btree

from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.app import getSchoolToolApplication
from schooltool.common import DateRange

from schooltool.term import interfaces
from schooltool.timetable import findRelatedTimetables


class Term(DateRange, contained.Contained, persistent.Persistent):

    zope.interface.implements(interfaces.ITerm, interfaces.ITermWrite)

    def __init__(self, title, first, last):
        super(Term, self).__init__(first, last)
        self.title = title
        self._schooldays = set()

    def _validate(self, date):
        if not date in self:
            raise ValueError("Date %r not in term [%r, %r]" %
                             (date, self.first, self.last))

    def isSchoolday(self, date):
        self._validate(date)
        if date in self._schooldays:
            return True
        return False

    def add(self, date):
        self._validate(date)
        self._schooldays.add(date)
        self._schooldays = self._schooldays  # persistence

    def remove(self, date):
        self._validate(date)
        self._schooldays.remove(date)
        self._schooldays = self._schooldays  # persistence

    def addWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays:
                self.add(date)

    def removeWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays and self.isSchoolday(date):
                self.remove(date)

    def toggleWeekdays(self, *weekdays):
        for date in self:
            if date.weekday() in weekdays:
                if self.isSchoolday(date):
                    self.remove(date)
                else:
                    self.add(date)

    def reset(self, first, last):
        if last < first:
            # import timemachine
            raise ValueError("Last date %r less than first date %r" %
                             (last, first))
        self.first = first
        self.last = last
        self._schooldays.clear()


class TermContainer(btree.BTreeContainer):

    zope.interface.implements(interfaces.ITermContainer, IAttributeAnnotatable)


def getTermForDate(date):
    """Find the term that contains `date`.

    Returns None if `date` falls outside all terms.
    """
    terms = getSchoolToolApplication()["terms"]
    for term in terms.values():
        if date in term:
            return term
    else:
        return None


def getNextTermForDate(date):
    """Find the term that contains `date`, or the next one.

    If there is a term that contains `date`, it is returned.  Otherwise, the
    first term that starts after `date` is returned.  If there are none,
    the last term that ended before `date` is returned.

    Returns None if there are no terms.
    """
    terms = getSchoolToolApplication()["terms"]
    before, after = [], []
    for term in terms.values():
        if date in term:
            return term
        if date > term.last:
            before.append((term.last, term))
        if date < term.first:
            after.append((term.first, term))
    if after:
        return min(after)[1]
    if before:
        return max(before)[1]
    return None


class DateManagerUtility(object):
    zope.interface.implements(interfaces.IDateManager)

    @property
    def today(self):
        app = ISchoolToolApplication(None)
        tzinfo = pytz.timezone(IApplicationPreferences(app).timezone)
        dt = pytz.utc.localize(datetime.utcnow())
        return dt.astimezone(tzinfo).date()
