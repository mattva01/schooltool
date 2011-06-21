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
group views.

$Id$
"""
from zope.cachedescriptors.property import Lazy
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.intid.interfaces import IIntIds
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.interface import implements, directlyProvides
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.component import adapts
from zope.component import getUtility
from zope.component import getMultiAdapter
from zope.security.checker import canAccess
from zope.i18n.interfaces.locales import ICollator
from zope.viewlet.viewlet import ViewletBase

from zc.table import table, column
from zc.table.interfaces import ISortableColumn

from schooltool.common import SchoolToolMessage as _
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.skin.containers import TableContainerView
from schooltool.app.browser.app import BaseAddView, BaseEditView
from schooltool.person.interfaces import IPerson
from schooltool.course.interfaces import ISection
from schooltool.table.interfaces import ITableFormatter
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.group.interfaces import IGroupMember
from schooltool.group.interfaces import IGroupContainer, IGroupContained
from schooltool.app.browser.app import RelationshipViewBase
from schooltool.app.browser.app import FlourishRelationshipViewBase
from schooltool.table.table import FilterWidget
from schooltool.table.table import SchoolToolTableFormatter
from schooltool.table.table import stupid_form_key

from schooltool.skin.flourish.viewlet import Viewlet


class GroupContainerAbsoluteURLAdapter(BrowserView):

    adapts(IGroupContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        container_id = int(self.context.__name__)
        int_ids = getUtility(IIntIds)
        container = int_ids.getObject(container_id)
        url = str(getMultiAdapter((container, self.request), name='absolute_url'))
        return url + '/groups'

    __call__ = __str__


class GroupContainerView(TableContainerView):
    """A Group Container view."""

    __used_for__ = IGroupContainer

    index_title = _("Group index")


class GroupListView(RelationshipViewBase):
    """View for managing groups that a person or a resource belongs to."""

    __used_for__ = IGroupMember

    @property
    def title(self):
        return _("Groups of ${person}", mapping={'person': self.context.title})
    current_title = _("Current Groups")
    available_title = _("Available Groups")

    def getSelectedItems(self):
        """Return a list of groups the current user is a member of."""
        return [group for group in self.context.groups
                if not ISection.providedBy(group)]

    def getAvailableItemsContainer(self):
        app = ISchoolToolApplication(None)
        groups = IGroupContainer(app, {})
        return groups

    def getCollection(self):
        return self.context.groups


class GroupView(BrowserView):
    """A Group info view."""

    __used_for__ = IGroupContained

    def renderPersonTable(self):
        persons = ISchoolToolApplication(None)['persons']
        formatter = getMultiAdapter((persons, self.request), ITableFormatter)
        formatter.setUp(table_formatter=table.StandaloneFullFormatter,
                        items=self.getPersons(),
                        batch_size=0)
        return formatter.render()

    def getPersons(self):
        return [member for member in self.context.members
                if canAccess(member, 'title')]

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


class MemberViewPersons(RelationshipViewBase):
    """View class for adding / removing members to / from a group."""

    __used_for__ = IGroupContained

    @property
    def title(self):
        return _("Members of ${group}", mapping={'group': self.context.title})
    current_title = _("Current Members")
    available_title = _("Add Members")

    def getSelectedItems(self):
        """Return a list of current group memebers."""
        return filter(IPerson.providedBy, self.context.members)

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']

    def getCollection(self):
        return self.context.members


class GroupAddView(BaseAddView):
    """A view for adding a group."""


class GroupEditView(BaseEditView):
    """A view for editing group info."""

    __used_for__ = IGroupContained


class GroupsViewlet(ViewletBase):
    """A viewlet showing the groups a person is in."""

    def update(self):
        self.collator = ICollator(self.request.locale)
        groups = [
            group for group in self.context.groups
            if (canAccess(group, 'title') and
                not ISection.providedBy(group))]

        schoolyears_data = {}
        for group in groups:
            sy = ISchoolYear(group.__parent__)
            if sy not in schoolyears_data:
                schoolyears_data[sy] = []
            schoolyears_data[sy].append(group)

        self.schoolyears = []
        for sy in sorted(schoolyears_data, key=lambda x:x.first, reverse=True):
            sy_info = {'obj': sy,
                       'groups': sorted(schoolyears_data[sy],
                                        cmp=self.collator.cmp,
                                        key=lambda x:x.title)}
            self.schoolyears.append(sy_info)

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


class FlourishGroupsViewlet(Viewlet):
    """A flourish viewlet showing the groups a person is in."""

    template = ViewPageTemplateFile('f_groupsviewlet.pt')
    body_template = None
    render = lambda self, *a, **kw: self.template(*a, **kw)

    def update(self):
        self.collator = ICollator(self.request.locale)
        groups = [
            group for group in self.context.groups
            if (canAccess(group, 'title') and
                not ISection.providedBy(group))]

        schoolyears_data = {}
        for group in groups:
            sy = ISchoolYear(group.__parent__)
            if sy not in schoolyears_data:
                schoolyears_data[sy] = []
            schoolyears_data[sy].append(group)

        self.schoolyears = []
        for sy in sorted(schoolyears_data, key=lambda x:x.first, reverse=True):
            sy_info = {'obj': sy,
                       'groups': sorted(schoolyears_data[sy],
                                        cmp=self.collator.cmp,
                                        key=lambda x:x.title)}
            self.schoolyears.append(sy_info)

    @property
    def canModify(self):
        return canAccess(self.context.__parent__, '__delitem__')


class CSSFormatter(table.FormFullFormatter):

    def renderHeaders(self):
        result = []
        old_css_class = self.cssClasses.get('th')
        for index, col in enumerate(self.visible_columns):
            self.cssClasses['th'] = 'column-' + str(index)
            result.append(self.renderHeader(col))
        self.cssClasses['th'] = old_css_class
        return ''.join(result)


class FlourishGroupFilterWidget(FilterWidget):

    template = ViewPageTemplateFile('f_group_filter.pt')


class FlourishGroupTableFormatter(SchoolToolTableFormatter):

    def render(self):
        formatter = self._table_formatter(
            self.context, self.request, self._items,
            columns=self._columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self._sort_on,
            prefix=self.prefix)
        formatter.cssClasses['table'] = 'groups-relationship-table'
        return formatter()

    def sortOn(self):
        return (('schoolyear', False), ("title", False))


class ActionColumn(column.Column):

    def __init__(self, prefix, name=None, label=None, id_getter=None):
        self.name = name
        self.title = _(u'Action')
        self.prefix = prefix
        self.label = label
        if id_getter is None:
            self.id_getter = stupid_form_key
        else:
            self.id_getter = id_getter

    def renderCell(self, item, formatter):
        form_id = ".".join(filter(None, [self.prefix, self.id_getter(item)]))
        return '<input type="submit" value="%s" name="%s" />' % (self.label,
                                                                 form_id)


class FlourishGroupListView(FlourishRelationshipViewBase):

    current_title = _('Current Groups')
    available_title = _('Available Groups')

    @Lazy
    def schoolyears(self):
        app = ISchoolToolApplication(None)
        schoolyears = ISchoolYearContainer(app)
        active_schoolyear = schoolyears.getActiveSchoolYear()
        return [schoolyear for schoolyear in schoolyears.values()
                if schoolyear.first >= active_schoolyear.first]

    def getSelectedItems(self):
        return [group for group in self.getCollection()
                if not ISection.providedBy(group) and
                ISchoolYear(group.__parent__) in self.schoolyears]

    def getAvailableItemsContainer(self):
        app = ISchoolToolApplication(None)
        groups = IGroupContainer(app, {})
        return groups

    def getAvailableItems(self):
        result = []
        selected_items = set(self.getSelectedItems())
        for schoolyear in self.schoolyears:
            groups = IGroupContainer(schoolyear)
            result.extend([group for group in groups.values()
                           if group not in selected_items])
        return result

    def getCollection(self):
        return self.context.groups

    def getColumnsAfter(self, prefix):
        schoolyear = column.GetterColumn(
            name='schoolyear',
            title=_(u'School Year'),
            getter=lambda i, f: ISchoolYear(i.__parent__).title,
            subsort=True)
        directlyProvides(schoolyear, ISortableColumn)
        if prefix == 'add_item':
            action = ActionColumn(prefix, 'add', _('Add'), self.getKey)
        elif prefix == 'remove_item':
            action = ActionColumn(prefix, 'remove', _('Remove'), self.getKey)
        return [schoolyear, action]

    def createTableFormatter(self, **kwargs):
        kwargs['columns_after'] = self.getColumnsAfter(kwargs['prefix'])
        kwargs['table_formatter'] = CSSFormatter
        container = self.getAvailableItemsContainer()
        formatter = getMultiAdapter((container, self.request),
                                    ITableFormatter)
        formatter.setUp(**kwargs)
        return formatter

    def setUpTables(self):
        self.available_table = self.createTableFormatter(
            ommit=self.getOmmitedItems(),
            items=self.getAvailableItems(),
            prefix="add_item")
        self.selected_table = self.createTableFormatter(
            filter=lambda l: l,
            items=self.getSelectedItems(),
            prefix="remove_item",
            batch_size=0)

    def getKey(self, item):
        schoolyear = ISchoolYear(item.__parent__)
        return "%s.%s" % (schoolyear.__name__, item.__name__)
