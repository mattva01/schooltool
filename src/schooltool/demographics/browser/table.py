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

from zope.interface import implements, directlyProvides
from zope.app import zapi
from zope.formlib import form
from zope.security.checker import canAccess
from zope.security.proxy import removeSecurityProxy
from zope.app.dependable.interfaces import IDependable
from zc.table.interfaces import IColumn, ISortableColumn
from zc.table import column
from zc.table.column import GetterColumn
from zope.app.pagetemplate import ViewPageTemplateFile
from hurry.query.interfaces import IQuery
from hurry.query import query
from schooltool.app.browser import ViewPreferences
from schooltool.demographics import interfaces
from schooltool.skin.table import TablePage

class PersonTable(TablePage):
    __call__ = ViewPageTemplateFile('table.pt')
        
    def columns(self):
        username = GetterColumn(
            name='username',
            title=u'Username',
            getter=lambda i, f: i.username,
            subsort=True)
        directlyProvides(username, ISortableColumn)
        full_name = GetterColumn(
            name='full_name',
            title=u'Full name',
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(full_name, ISortableColumn)
        birth_date = DateColumn(
            name='birth_date',
            title=u'Birth',
            getter=lambda i, f: i.demographics.birth_date,
            subsort=True)
        directlyProvides(birth_date, ISortableColumn)
        enrollment_date = DateColumn(
            name='enrollment_date',
            title=u'Enrollment',
            getter=lambda i, f: i.schooldata.enrollment_date,
            subsort=True)
        directlyProvides(enrollment_date, ISortableColumn)
        modified = ModifiedColumn(
            name='modified',
            title=u'Modified',
            subsort=True)
        directlyProvides(modified, ISortableColumn)
        
        return [
            DeleteCheckBoxColumn(name='delete', title=u''),
            username,
            full_name,
            birth_date,
            enrollment_date,
            modified,
            EditColumn(name='edit', title=u'Edit'),
            DisplayColumn(name='display', title=u'Display')
            ]

    def values(self):
        return self.context.values()

    def sortOn(self):
        return (("modified", True),)

    @property
    def canModify(self):
        return canAccess(self.context, '__delitem__')
    
class SearchTable(form.FormBase, PersonTable):
    form_fields = form.Fields(interfaces.ISearch, render_context=False)
    template = ViewPageTemplateFile('search.pt')
    
    def __init__(self, context, request):
        super(SearchTable, self).__init__(context, request)
        self.search_data = {}
   
    @form.action("submit")
    def handle_submit(self, action, data):
        self.search_data = data
        
    def values(self):
        if not self.search_data:
            return []
        # XXX Some search problems seem to occur in the underlying Zope 3
        # text index code:
        # - *a* matches "Alpha" but not "Beta"
        # - queries smaller than three letters result in a parsetree.ParseError
        #   exception.
        q = zapi.getUtility(IQuery)
        s = None
        fulltext = self.search_data['fulltext']
        if fulltext:
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
        result = super(SearchTable, self).extraUrl()
        return result + self.searchOptions()

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

    def sortOn(self):
        return (("modified", True),)
    
class EditColumn(column.Column):
    def renderCell(self, item, formatter):
        return '<a href="%s">Edit</a>' % (
            zapi.absoluteURL(item, formatter.request) + '/nameinfo/@@edit.html')

class DisplayColumn(column.Column):
    def renderCell(self, item, formatter):
        return '<a href="%s">Display</a>' % (
            zapi.absoluteURL(item, formatter.request) + '/nameinfo')

class DeleteCheckBoxColumn(column.Column):
    def renderCell(self, item, formatter):
        if self.hasDependents(item):
            return (
                '<input type="checkbox" name="delete.%s" disabled="disabled" />'
                % item.username)
        else:
            return '<input type="checkbox" name="delete.%s" />' % item.username

    def hasDependents(self, item):
        # We cannot adapt security-proxied objects to IDependable.  Unwrapping
        # is safe since we do not modify anything, and the information whether
        # an object can be deleted or not is not classified.
        unwrapped_context = removeSecurityProxy(item)
        dependable = IDependable(unwrapped_context, None)
        if dependable is None:
            return False
        else:
            return bool(dependable.dependents())

class ModifiedColumn(column.SortingColumn):
    _renderDatetime = None

    def getSortKey(self, item, formatter):
        return item.modified
    
    def renderCell(self, item, formatter):
        # cache _renderDatetime for performance
        if self._renderDatetime is None:
            self._renderDatetime = ViewPreferences(
                formatter.request).renderDatetime
        return self._renderDatetime(item.modified)

class DateColumn(column.GetterColumn):
    """ Column for rendering dates when None values can be around. """

    def getSortKey(self, item, formatter):
        if self.getter(item, formatter) is None:
            return date.min
        else:
            return self.getter(item, formatter)
