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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool calendar event views.
"""
import urllib
import datetime

import zope.formlib.interfaces
import zope.formlib.widget
from zope import formlib
from zope.i18n import translate
from zope.interface import Interface
from zope.cachedescriptors.property import Lazy
from zope.component import getMultiAdapter
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.absoluteurl import absoluteURL

import zc.table.table
import z3c.form.browser.radio
from z3c.form import form, field, button

import schooltool.skin.flourish.page
import schooltool.skin.flourish.form
from schooltool.app.browser import ViewPreferences
from schooltool.app.browser.cal import CalendarEventView
from schooltool.app.browser.cal import ICalendarEventAddForm
from schooltool.app.browser.cal import CalendarEventAddView
from schooltool.app.browser.cal import ICalendarEventEditForm
from schooltool.app.browser.cal import CalendarEventEditView
from schooltool.app.browser.cal import CalendarEventBookingView
from schooltool.app.utils import vocabulary
from schooltool.calendar.app import CalendarEvent
from schooltool.calendar.interfaces import ICalendar
from schooltool.calendar.utils import parse_date
from schooltool.skin import flourish
from schooltool.table.table import ImageInputColumn
from schooltool.table.table import label_cell_formatter_factory

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
        custom_factory = formlib.widget.CustomWidgetFactory(
            factory, cssClass="date-field", **kw)
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

    def setUpCustomWidgets(self):
        self.setCustomWidget('description', height=5)
        self.setCustomWidget('exceptions', width=20, height=5)

    def _setUpWidgets(self):
        self.setUpCustomWidgets()
        super(FlourishCalendarEventAddView, self)._setUpWidgets()


class FlourishCalendarEventBookingView(flourish.page.Page,
                                       CalendarEventBookingView):

    update = CalendarEventBookingView.update

    def renderBookedTable(self):
        prefix = "remove_item"
        available_columns = self.columns()
        available_columns[0].cell_formatter = label_cell_formatter_factory(prefix)
        available_columns[2].title = _('Reserved by others')
        columns = list(available_columns)

        title=_('Release resource')
        # XXX: this getter is just plain wrong
        getter = lambda r: r.__name__

        remove_column = ImageInputColumn(
            prefix, name='action',
            title=title, alt=title,
            library='schooltool.skin.flourish',
            image='remove-icon.png', id_getter=getter)
        columns.append(remove_column)

        formatter = zc.table.table.FormFullFormatter(
            self.context, self.request, self.getBookedItems(),
            columns=columns,
            sort_on=self.sortOn(),
            prefix="booked")
        formatter.cssClasses['table'] = 'data'

        return formatter()

    def renderAvailableTable(self):
        prefix = "add_item"
        available_columns = self.columns()
        available_columns[0].cell_formatter = label_cell_formatter_factory(prefix)
        available_columns[2].title = _('Reserved by others')
        columns = list(available_columns)

        title=_('Reserve resource')
        # XXX: this getter is just plain wrong
        getter = lambda r: r.__name__

        add_column = ImageInputColumn(
            prefix, name='action',
            title=title, alt=title,
            library='schooltool.skin.flourish',
            image='add-icon.png', id_getter=getter)
        columns.append(add_column)

        formatter = zc.table.table.FormFullFormatter(
            self.context, self.request, self.filter(self.availableResources),
            columns=columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self.sortOn(),
            prefix="available")
        formatter.cssClasses['table'] = 'data'


        return formatter()


class IDeleteRecurringEventForm(Interface):

    delete = zope.schema.Choice(
        title=_("Delete"),
        vocabulary=vocabulary([
                ("all", _("All occurrences of this event")),
                ("current", _("Only current occurrence")),
                ("future", _("This and all future occurrences"))]),
        default="current",
        required=True,
        )


class DeleteEventDialog(flourish.form.DialogForm):
    """A view for deleting events."""

    dialog_submit_actions = ('delete',)
    dialog_close_actions = ('cancel',)
    label = None
    data = None

    @Lazy
    def event(self):
        event_id = self.request.get('event_id', None)
        if event_id is None:
            return None
        try:
            return self.context.find(event_id)
        except KeyError:
            return None

    @Lazy
    def date(self):
        event_date = self.request.get('date', None)
        if event_date is None:
            return None
        return parse_date(event_date)

    def initDialog(self):
        super(DeleteEventDialog, self).initDialog()
        title = _(u'Delete event ${event}',
                  mapping={'event': self.event.title})
        self.ajax_settings['dialog']['title'] = translate(
            title, context=self.request)

    def nextURL(self):
        return (self.request.get('back_url') or
                absoluteURL(self.context, self.request))

    @Lazy
    def recurrent(self):
        return self.event.recurrence is not None

    @Lazy
    def day_title(self):
        preferences = ViewPreferences(self.request)
        dayformat = '%A, ' + preferences.dateformat
        return unicode(self.event.dtstart.strftime(dayformat))

    def modifyRecurrence(self, event, **kwargs):
        """Modify the recurrence rule of an event.

        If the event does not have any recurrences afterwards, it is removed
        from the parent calendar
        """
        rrule = event.recurrence
        new_rrule = rrule.replace(**kwargs)
        # This view requires the modifyEvent permission.
        event.recurrence = removeSecurityProxy(new_rrule)
        if not event.hasOccurrences():
            ICalendar(event).removeEvent(removeSecurityProxy(event))

    def deleteCurrent(self):
        exceptions = self.event.recurrence.exceptions + (self.date, )
        self.modifyRecurrence(self.event, exceptions=exceptions)

    def deleteFuture(self):
        self.modifyRecurrence(
            self.event, until=(self.date - datetime.timedelta(1)),
            count=None)

    def deleteAll(self):
        self.context.removeEvent(removeSecurityProxy(self.event))

    delete_handlers = {
        'all': deleteAll,
        'current': deleteCurrent,
        'future': deleteFuture,
        }

    def updateActions(self):
        super(DeleteEventDialog, self).updateActions()
        self.actions['delete'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def update(self):
        self.data = {}
        if self.recurrent:
            self.fields = field.Fields(IDeleteRecurringEventForm)
            radio_widget = z3c.form.browser.radio.RadioFieldWidget
            self.fields['delete'].widgetFactory = radio_widget
        super(DeleteEventDialog, self).update()

    def getContent(self):
        return self.data

    @button.buttonAndHandler(_("Delete"), name='delete')
    def handleDelete(self, action):
        data, errors = self.extractData()
        if self.recurrent:
            handler = self.delete_handlers.get(data['delete'], None)
        else:
            handler = self.delete_handlers['all']

        if handler is not None:
            next_url = self.nextURL()
            handler(self)
            self.request.response.redirect(next_url.encode('utf-8'))
            self.ajax_settings['dialog'] = 'close'

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        pass


class EventLinks(flourish.page.RefineLinksViewlet):
    """Manager for Action links in event views."""


class DeleteEventLinkViewlet(flourish.page.ModalFormLinkViewlet):

    @property
    def calendar(self):
        return ICalendar(self.event)

    @property
    def event(self):
        return self.context

    def nextURL(self):
        try:
            return self.view.nextURL()
        except AttributeError:
            return absoluteURL(self.calendar, self.request)

    @property
    def url(self):
        preferences = ViewPreferences(self.request)
        event = self.event
        start = event.dtstart.astimezone(preferences.timezone)
        url = '%s/delete.html?event_id=%s&date=%s&back_url=%s' % (
            absoluteURL(self.calendar, self.request),
            event.unique_id,
            start.strftime('%Y-%m-%d'),
            urllib.quote(self.nextURL()))
        return url

