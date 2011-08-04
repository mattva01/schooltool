#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
SchoolTool calendar event views.
"""

import zope.formlib.interfaces
import zope.formlib.widget
from zope import formlib
from zope.component import getMultiAdapter

import schooltool.skin.flourish.page
from schooltool.calendar.app import CalendarEvent
from schooltool.app.browser.cal import CalendarEventView
from schooltool.app.browser.cal import ICalendarEventAddForm
from schooltool.app.browser.cal import CalendarEventAddView
from schooltool.app.browser.cal import ICalendarEventEditForm
from schooltool.app.browser.cal import CalendarEventEditView
from schooltool.app.browser.cal import CalendarEventBookingView
from schooltool.skin import flourish

from schooltool.common import SchoolToolMessage as _


calendarFieldNames = (
    "title", "allday", "start_date", "start_time", "duration",
    "duration_type", "recurrence", "location", "description",
    "recurrence_type", "interval", "range", "until", "count",
    "monthly", "exceptions", "weekdays",
    )


class FlourishCalendarEventView(flourish.page.Page,
                                CalendarEventView):
    pass


class FlourishCalendarEventEditView(flourish.page.Page,
                                    CalendarEventEditView):
    schema = ICalendarEventEditForm
    fieldNames = calendarFieldNames

    update = CalendarEventEditView.update

    def setCustomWidget(self, name, **kw):
        factory = lambda field, request: getMultiAdapter(
            (field, self.request), formlib.interfaces.IInputWidget)
        custom_factory = formlib.widget.CustomWidgetFactory(factory, **kw)
        setattr(self, str(name+'_widget'), custom_factory)

    def _setUpWidgets(self):
        self.setCustomWidget('description', height=5)
        self.setCustomWidget('exceptions', width=20, height=5)
        super(FlourishCalendarEventEditView, self)._setUpWidgets()


class FlourishCalendarEventAddView(flourish.page.Page,
                                   CalendarEventAddView):
    schema = ICalendarEventAddForm
    fieldNames = calendarFieldNames

    update = CalendarEventAddView.update

    _arguments = ()
    _keyword_arguments = calendarFieldNames
    _set_after_add = ()
    _set_before_add = None
    _factory = CalendarEvent

    def setCustomWidget(self, name, **kw):
        factory = lambda field, request: getMultiAdapter(
            (field, self.request), formlib.interfaces.IInputWidget)
        custom_factory = formlib.widget.CustomWidgetFactory(factory, **kw)
        setattr(self, str(name+'_widget'), custom_factory)

    def _setUpWidgets(self):
        self.setCustomWidget('description', height=5)
        self.setCustomWidget('exceptions', width=20, height=5)
        super(FlourishCalendarEventAddView, self)._setUpWidgets()


class FlourishCalendarEventBookingView(flourish.page.Page,
                                       CalendarEventBookingView):

    update = CalendarEventBookingView.update

    @property
    def subtitle(self):
        return _('Resource booking for ($title)',
                 mapping={'title': self.context.title})
