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
from zope.component import adapts
from zope.interface import directlyProvides
from zope.traversing.browser.absoluteurl import absoluteURL

from zc.table.interfaces import ISortableColumn

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.skin import flourish
from schooltool.task.interfaces import IRemoteTask
from schooltool.task.tasks import TaskReadStatus
from schooltool import table

from schooltool.common import SchoolToolMessage as _


class TaskContainer(flourish.page.Page):

    @property
    def tasks(self):
        return sorted(self.context.values(), key=lambda t: (str(t.scheduled), t.task_id))


class TaskStatus(flourish.page.Page):

    @Lazy
    def status(self):
        return TaskReadStatus(self.task_id)

    @property
    def task_id(self):
        return self.context.task_id


class TaskContainerLinkViewlet(flourish.page.LinkViewlet):

    def url(self):
        app = ISchoolToolApplication(None)
        base_url = absoluteURL(app, self.request)
        return '%s/%s' % (base_url, 'schooltool.tasks')


def task_state_formatter(value, item, formatter):
    cls = ""
    if value.strip() == 'FAILURE':
        cls = "error"
    return '<p%s>%s</p>' % (
        (' class="%s"') % cls if cls else '', value)


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
            title=_(u'Status'),
            getter=lambda i, f: i.internal_state,
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


class TaskTableDevmode(TaskTable):

    task_id_formatter = lambda self, *a: task_id_debug_cell_formatter(*a)
