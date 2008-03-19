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
from datetime import date

from zope.interface import directlyProvides
from zope.component import getUtility
from zope.formlib import form
from zc.table.interfaces import ISortableColumn
from zc.table import column
from zc.table import table
from zc.table.column import GetterColumn
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.i18n import translate
from hurry.query.interfaces import IQuery
from hurry.query import query
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.browser import ViewPreferences
from schooltool.person.browser.person import PersonContainerView
from schooltool.table.table import DependableCheckboxColumn
from schooltool.demographics import interfaces
from schooltool.common import SchoolToolMessage as _


class PersonTable(PersonContainerView):
    """Browse persons in a table.
    """
    template = ViewPageTemplateFile('table.pt')

    def __init__(self, context, request):
        # anyone who can see this view can see infomration for the
        # container and persons in it
        context = removeSecurityProxy(context)
        super(PersonTable, self).__init__(context, request)

    def setUpTableFormatter(self, formatter):
        columns_before = []
        if self.canModify():
            columns_before = [DependableCheckboxColumn(prefix="delete",
                                                       name='delete_checkbox',
                                                       title=u'')]
        formatter.setUp(columns=self.columns(),
                        sort_on=self.sortOn(),
                        columns_before=columns_before)

    def columns(self):
        username = GetterColumn(
            name='username',
            title=_(u'Username'),
            getter=lambda i, f: i.username,
            subsort=True)
        directlyProvides(username, ISortableColumn)
        full_name = FullnameColumn(
            name='full_name',
            title=_(u'Full name'),
            subsort=True)
        directlyProvides(full_name, ISortableColumn)
        birth_date = DateColumn(
            name='birth_date',
            title=_(u'Birth'),
            getter=lambda i, f: (i.demographics.birth_date or ''),
            subsort=True)
        directlyProvides(birth_date, ISortableColumn)
        enrollment_date = DateColumn(
            name='enrollment_date',
            title=_(u'Enrollment'),
            getter=lambda i, f: (i.schooldata.enrollment_date or ''),
            subsort=True)
        directlyProvides(enrollment_date, ISortableColumn)
        modified = ModifiedColumn(
            name='modified',
            title=_(u'Modified'),
            subsort=True)
        directlyProvides(modified, ISortableColumn)

        return [
            username,
            full_name,
            birth_date,
            enrollment_date,
            modified,
            EditColumn(name='edit', title=_(u'Edit')),
            DisplayColumn(name='display', title=_(u'Display'))
            ]

    def sortOn(self):
        return (("modified", True),)


class SearchTable(form.FormBase, PersonTable):
    """Browse person search results in a table.
    """
    form_fields = form.Fields(interfaces.ISearch, render_context=False)
    template = ViewPageTemplateFile('search.pt')

    def __init__(self, context, request):
        super(SearchTable, self).__init__(context, request)
        self.search_data = {}

    def setUpTableFormatter(self, formatter):
        columns_before = []
        if self.canModify():
            columns_before = [DependableCheckboxColumn(prefix="delete",
                                                       name='delete_checkbox',
                                                       title=u'')]
        formatter.setUp(items=self.values(),
                        columns=self.columns(),
                        sort_on=self.sortOn(),
                        columns_before=columns_before,
                        table_formatter=table.StandaloneFullFormatter)

    @form.action("submit")
    def handle_submit(self, action, data):
        self.search_data = data
        self.form_reset = False
        self.setUpTableFormatter(self.table)

    def setUpWidgets(self, ignore_request=False):
        form.FormBase.setUpWidgets(self, ignore_request)

    def values(self):
        if not self.search_data:
            return []
        # XXX Some search problems seem to occur in the underlying Zope 3
        # text index code:
        # - *a* matches "Alpha" but not "Beta"
        # - queries smaller than three letters result in a parsetree.ParseError
        #   exception.
        q = getUtility(IQuery)
        s = None
        fulltext = self.search_data['fulltext']
        if fulltext:
            if not fulltext.endswith('*'):
                fulltext += "*"
            s = query.Text(('demographics_catalog', 'fulltext'),
                           fulltext)
        parentName = self.search_data['parentName']
        if parentName:
            t = query.Text(('demographics_catalog', 'parentName'),
                               parentName)
            if s is None:
                s = t
            else:
                s = s & t
        studentId = self.search_data['studentId']
        if studentId:
            t = query.Eq(('demographics_catalog', 'studentId'), studentId)
            if s is None:
                s = t
            else:
                s = s & t
        # if we have no query at all
        if not s:
            return []
        return q.searchResults(s)

    def extraUrl(self):
        return self.searchOptions()

    def searchOptions(self):
        result = []
        form = self.request.form
        for key in form:
            if key.startswith('form.'):
                result.append((key, form[key]))
        if not result:
            return ''
        return '&' + '&'.join(['%s=%s' % (key, value)
                               for (key, value) in result])


class EditColumn(column.Column):
    """Table column that displays edit link.
    """
    def renderCell(self, item, formatter):
        return '<a href="%s">%s</a>' % (
            absoluteURL(item, formatter.request) + '/nameinfo/@@edit.html',
            translate(_("Edit"), formatter.request))


class DisplayColumn(column.Column):
    """Table column that displays display link.
    """
    def renderCell(self, item, formatter):
        return '<a href="%s">%s</a>' % (
            absoluteURL(item, formatter.request) + '/nameinfo',
            translate(_("Display"), formatter.request))


class FullnameColumn(column.GetterColumn):
    """Table column that displays full name as link.
    """
    def getSortKey(self, item, formatter):
        return item.nameinfo.last_name

    def getter(self, item, formatter):
        return item.title

    def cell_formatter(self, value, item, formatter):
        return '<a href="%s">%s</a>' % (
            absoluteURL(item, formatter.request) + '/nameinfo',
            value)


class ModifiedColumn(column.GetterColumn):
    """Table column that displays modified date, sortable.
    """
    _renderDatetime = None

    def getSortKey(self, item, formatter):
        return item.modified

    def getter(self, item, formatter):
        return item.modified

    def cell_formatter(self, value, item, formatter):
        # cache _renderDatetime for performance
        if self._renderDatetime is None:
            self._renderDatetime = ViewPreferences(
                formatter.request).renderDatetime
        return self._renderDatetime(value)


class DateColumn(column.GetterColumn):
    """Table column that displays dates.

    Sortable even when None values are around.
    """

    def getSortKey(self, item, formatter):
        if self.getter(item, formatter) is None:
            return date.min
        else:
            return self.getter(item, formatter)
