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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Term implementation
"""
import persistent
import pytz
from datetime import datetime

import zope.interface
from zope.event import notify
from zope.proxy import sameProxiedObjects
from zope.component import adapts
from zope.component import adapter
from zope.component import getUtility
from zope.interface import implements
from zope.interface import implementer
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.container import contained, btree

from schooltool.schoolyear.subscriber import EventAdapterSubscriber
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.schoolyear.interfaces import TermOverlapError
from schooltool.schoolyear.interfaces import ISubscriber
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common import IDateRange
from schooltool.common import DateRange

from schooltool.term.interfaces import TermDateNotInSchoolYear
from schooltool.term import interfaces
from schooltool.common import SchoolToolMessage as _


class TermBeforeChangeEvent(object):

    def __init__(self, term, old_dates, new_dates):
        self.term = term
        self.old_dates = old_dates
        self.new_dates = new_dates


class TermAfterChangeEvent(object):

    def __init__(self, term, old_dates, new_dates):
        self.term = term
        self.old_dates = old_dates
        self.new_dates = new_dates


class EmergencyDayEvent(object):

    def __init__(self, date, replacement_date):
        self.date = date
        self.replacement_date = replacement_date


class Term(DateRange, contained.Contained, persistent.Persistent):
    zope.interface.implements(interfaces.ITerm, interfaces.ITermWrite)

    def __init__(self, title, first, last):
        self.title = title
        self._first = first
        self._last = last
        self._schooldays = set()
        if last < first:
            raise ValueError("Last date %r less than first date %r" %
                             (last, first))

    @property
    def first(self):
        return self._first

    @first.setter
    def first(self, new_first_date):
        old_dates = (self._first, self._last)
        new_dates = (new_first_date, self._last)

        if self._last < new_first_date:
            raise ValueError("Last date %r less than first date %r" %
                             (self._last, new_first_date))

        notify(TermBeforeChangeEvent(self, old_dates, new_dates))
        self._first = new_first_date
        notify(TermAfterChangeEvent(self, old_dates, new_dates))

    @property
    def last(self):
        return self._last

    @last.setter
    def last(self, new_last_date):
        old_dates = (self._first, self._last)
        new_dates = (self._first, new_last_date)

        if new_last_date < self._first:
            raise ValueError("Last date %r less than first date %r" %
                             (new_last_date, self._first))

        notify(TermBeforeChangeEvent(self, old_dates, new_dates))
        self._last = new_last_date
        notify(TermAfterChangeEvent(self, old_dates, new_dates))

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
    """BBB: only there for backwards compatibility."""


def getTermForDate(date):
    """Find the term that contains `date`.

    Returns None if `date` falls outside all terms.
    """
    terms = interfaces.ITermContainer(date, {})
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
    terms = interfaces.ITermContainer(date, {})
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


def listTerms(context):
    """List terms of a schoolyear in a chronological order."""
    terms = interfaces.ITermContainer(context, {})
    return sorted(terms.values(), key=lambda t: t.first)


def getPreviousTerm(term):
    """Get the next term in the same SchoolYear.

    The limitation is imposed as SchoolYears are strictly separated
    entities (for archival purposes).
    """
    prev_terms = [t for t in listTerms(term)
                  if t.last < term.first]
    if prev_terms:
        return prev_terms[-1]
    return None


def getNextTerm(term):
    """Get the next term in the same SchoolYear.

    The limitation is imposed as SchoolYears are strictly separated
    entities (for archival purposes).
    """
    next_terms = [t for t in listTerms(term)
                  if t.first > term.last]
    if next_terms:
        return next_terms[0]
    return None


class DateManagerUtility(object):
    zope.interface.implements(interfaces.IDateManager)

    @property
    def today(self):
        app = ISchoolToolApplication(None)
        tzinfo = pytz.timezone(IApplicationPreferences(app).timezone)
        dt = pytz.utc.localize(datetime.utcnow())
        return dt.astimezone(tzinfo).date()

    @property
    def current_term(self):
        return getNextTermForDate(self.today)


class TodayDescriptor(object):

    def __init__(self, request):
        self.request = request
        app = ISchoolToolApplication(None)
        self.tzinfo = pytz.timezone(IApplicationPreferences(app).timezone)

    def __get__(self, instance, owner):
        dateman = getUtility(interfaces.IDateManager)
        if dateman is not None:
            return dateman.today
        dt = pytz.utc.localize(datetime.utcnow())
        return dt.astimezone(self.tzinfo).date()


class TimeNowDescriptor(object):

    def __init__(self, request):
        self.request = request
        app = ISchoolToolApplication(None)
        self.tzinfo = pytz.timezone(IApplicationPreferences(app).timezone)

    def __get__(self, instance, owner):
        dt = pytz.utc.localize(datetime.utcnow())
        return dt.astimezone(self.tzinfo)


@implementer(interfaces.ITermContainer)
def getTermContainer(context):
    app = ISchoolToolApplication(None)
    syc = ISchoolYearContainer(app)
    return syc.getActiveSchoolYear()


@adapter(interfaces.ITerm)
@implementer(ISchoolYear)
def getSchoolYearForTerm(term):
    return term.__parent__


class RemoveTermsWhenSchoolYearIsDeleted(ObjectEventAdapterSubscriber):
    adapts(IObjectRemovedEvent, ISchoolYear)

    def __call__(self):
        for term_id in list(self.object.keys()):
            del self.object[term_id]


def validateTermsForOverlap(sy, dr, term):
    overlapping_terms = []
    for other_term in sy.values():
        if (not sameProxiedObjects(other_term, term) and
            dr.overlaps(IDateRange(other_term))):
            overlapping_terms.append(other_term)
            if overlapping_terms:
                raise TermOverlapError(term,
                                       overlapping_terms)


class TermOverlapValidationSubscriber(EventAdapterSubscriber):
    adapts(TermBeforeChangeEvent)
    implements(ISubscriber)

    def __call__(self):
        sy = self.event.term.__parent__
        dr = DateRange(*self.event.new_dates)
        if sy:
            validateTermsForOverlap(sy, dr, self.event.term)


class TermOverflowValidationSubscriber(EventAdapterSubscriber):
    adapts(TermBeforeChangeEvent)
    implements(ISubscriber)

    def __call__(self):
        if self.event.term.__parent__ is None:
            return
        dr = IDateRange(self.event.term.__parent__)
        if (self.event.new_dates[0] not in dr or
            self.event.new_dates[1] not in dr):
            raise TermDateNotInSchoolYear(_("Term date is not in the school year."))
