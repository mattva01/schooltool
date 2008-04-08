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
Timetable specific calendar views.

$Id$
"""
from zope.viewlet.interfaces import IViewlet
from zope.interface import implements
from zope.cachedescriptors.property import CachedProperty

from schooltool.app.browser.cal import YearlyCalendarView
from schooltool.term.term import getTermForDate


class TimetablingYearlyCalendarView(YearlyCalendarView):
    """Yearly calendar view that displays term information."""

    def __init__(self, context, request):
        super(YearlyCalendarView, self).__init__(context,request)
        self.numterms = 1
        self.calendar = None

    @CachedProperty
    def legend(self):
        numterms = 1
        legend = {}
        for quarter in self.getYear(self.cursor):
            for month in quarter:
                for week in month:
                    for day in week:
                        term = getTermForDate(day.date)
                        if term and not term in legend:
                            legend[term] = self.numterms
                            numterms += 1
        return legend

    def renderRow(self, week, month):
        result = []

        for day in week:
            term = getTermForDate(day.date)
            cssClass = "term%d" % self.legend.get(term, 0)

            result.append('<td class="cal_yearly_day">')
            if day.date.month == month:
                if day.today():
                    cssClass += ' today'
                # Let us hope that URLs will not contain < > & or "
                # This is somewhat related to
                #   http://issues.schooltool.org/issue96
                result.append('<a href="%s" class="%s">%s</a>' %
                              (self.calURL('daily', day.date), cssClass,
                               day.date.day))
            result.append('</td>')

        return "\n".join(result)


class TermLegendViewlet(object):
    implements(IViewlet)

    def legend(self):
        terms = self.__parent__.legend.items()
        terms.sort(key=lambda t: t[0].first)
        return [{'title': term.title,
                 'cssclass': "legend-item term%s" % cssClass}
                for term, cssClass in terms]
