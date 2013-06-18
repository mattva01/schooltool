#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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

from zope.cachedescriptors.property import Lazy
from zope.interface import directlyProvides
from zope.traversing.browser.absoluteurl import absoluteURL

import zc.table.column
from zc.table.interfaces import ISortableColumn

from schooltool import table
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.skin import flourish
from schooltool.person.interfaces import IPerson
from schooltool.task.interfaces import IRemoteTask
from schooltool.task.state import TaskReadState

from schooltool.common import SchoolToolMessage as _


class TaskContainerView(flourish.page.Page):

    @property
    def tasks(self):
        return sorted(self.context.values(), key=lambda t: (str(t.scheduled), t.task_id))


class TaskStatusView(flourish.page.Page):

    @property
    def status(self):
        return TaskReadState(self.task_id)

    @property
    def persistent_failed(self):
        task = self.persistent_task
        if task is None:
            return False
        return task.permanent_traceback is not None

    @property
    def persistent_finished(self):
        task = self.persistent_task
        if task is None:
            return False
        return task.permanent_result is not None

    @property
    def persistent_task(self):
        return self.context

    @property
    def task_id(self):
        return self.context.task_id


class TaskContainerLinkViewlet(flourish.page.LinkViewlet):

    def url(self):
        app = ISchoolToolApplication(None)
        base_url = absoluteURL(app, self.request)
        return '%s/%s' % (base_url, 'schooltool.tasks')


def task_state_formatter(task, item, formatter):
    result = []

    cls = ""
    if task.failed:
        cls = "error"
    elif task.succeeded or task.working:
        cls = "success"
    else:
        cls = "info"
    internal_state = task.internal_state or ''
    if internal_state:
        result.append(
            '<p%s>%s</p>' % (
                (' class="%s"') % cls if cls else '', internal_state))
    if task.permanent_traceback is not None:
        result.append('<p class="error">TRACEBACK</p>')
    if task.permanent_result is not None:
        result.append('<p class="success">PERSISTED RESULT</p>')
    return '\n'.join(result)


def task_id_cell_formatter(value, item, formatter):
    url = absoluteURL(item, formatter.request)
    result = '''
      <p>
        <a href=%s>%s</a>
      </p>
    ''' % (url, value)
    return result


def task_id_debug_cell_formatter(value, item, formatter):
    result = task_id_cell_formatter(value, item, formatter)
    app_url = absoluteURL(ISchoolToolApplication(None), formatter.request)
    result += '''
      <p>
        <a href="%s/schooltool.task_results/%s">%s</a>
      </p>
      ''' % (app_url, value, _('JSON result'))
    return result


class TaskTable(table.ajax.IndexedTable):

    no_default_url_cell_formatter = True
    task_id_formatter = lambda self, *a: task_id_cell_formatter(*a)

    def sortOn(self):
        return (('scheduled', True),)

    def columns(self):
        task_id = table.column.IndexedGetterColumn(
            index='task_id',
            name='task_id',
            cell_formatter=self.task_id_formatter,
            title=_(u'Task ID'),
            getter=lambda i, f: i.task_id,
            subsort=True)
        signature = table.table.GetterColumn(
            name='signature',
            title=_(u'Signature'),
            getter=lambda i, f: i.signature,
            subsort=True)
        internal_state = table.column.IndexedGetterColumn(
            index='internal_state',
            name='internal_state',
            title=_(u'Internal state'),
            getter=lambda i, f: i,
            cell_formatter=task_state_formatter,
            subsort=True)
        directlyProvides(internal_state, ISortableColumn)
        scheduled = table.column.IndexedGetterColumn(
            index='scheduled',
            name='scheduled',
            title=_(u'Scheduled'),
            getter=lambda i, f: i.scheduled,
            cell_formatter=table.table.datetime_formatter,
            subsort=True)
        directlyProvides(scheduled, ISortableColumn)
        return [task_id, signature, internal_state, scheduled]

    def setUp(self, *args, **kw):
        super(TaskTable, self).setUp(*args, **kw)
        self.css_classes['table'] = 'data schooltool-tasks-status'


class TaskTableDevmode(TaskTable):

    task_id_formatter = lambda self, *a: task_id_debug_cell_formatter(*a)


class MessageColumn(zc.table.column.GetterColumn):

    def renderCell(self, item, formatter):
        content = flourish.content.queryContentProvider(
            item, formatter.request, getattr(formatter, 'view', None),
            'short')
        if content is None:
            return ''
        result = content()
        return result


class MessageDialog(flourish.form.Dialog):

    template = flourish.templates.File('templates/task_dialog.pt')
    refresh_delay = 10000

    @Lazy
    def form_id(self):
        return flourish.page.obj_random_html_id(self)


class TaskProgressDialog(flourish.form.Dialog):

    template = flourish.templates.File('templates/f_task_progress.pt')

    @property
    def main_recipient(self):
        person = IPerson(self.request, None)
        if self.context.recipients is None:
            return None
        recipients = sorted(self.context.recipients, key=lambda r: r.__name__)
        if person in recipients:
            return person
        for recipient in recipients:
            if flourish.canView(recipient):
                return recipient
        return None

    @property
    def task_id(self):
        return self.task and self.task.__name__

    @property
    def progress_id(self):
        return flourish.page.sanitize_id('progress-%s' % (self.task_id or self.__name__))

    @Lazy
    def task(self):
        sender = self.context.sender
        if IRemoteTask.providedBy(sender):
            return sender
        return None

    @property
    def failed(self):
        return self.task and self.task.failed

    @property
    def completed(self):
        return (self.task and (self.task.succeeded or
                               self.task.finished and not self.task.failed))

    @property
    def pending(self):
        return self.task and not self.task.finished

    @property
    def should_reload(self):
        sender = self.context.sender
        if IRemoteTask.providedBy(sender):
            return not sender.finished
        return False
