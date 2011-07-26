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
from zope.app.dependable.interfaces import IDependable
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
from zope.container.interfaces import INameChooser
from zope.security import checkPermission
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.i18n import translate
from z3c.form import field, button, form
from z3c.form.interfaces import HIDDEN_MODE
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
from schooltool.group.group import Group
from schooltool.group.interfaces import IGroup
from schooltool.group.interfaces import IGroupMember
from schooltool.group.interfaces import IGroupContainer, IGroupContained
from schooltool.app.browser.app import RelationshipViewBase
from schooltool.app.browser.app import FlourishRelationshipViewBase
from schooltool.table.table import FilterWidget
from schooltool.table.table import SchoolToolTableFormatter
from schooltool.table.table import LocaleAwareGetterColumn
from schooltool.skin.flourish.viewlet import Viewlet
from schooltool.common.inlinept import InheritTemplate
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.skin.flourish.containers import TableContainerView as FlourishTableContainerView
from schooltool.skin.flourish.containers import ContainerDeleteView
from schooltool.skin.flourish.page import RefineLinksViewlet
from schooltool.skin.flourish.page import LinkViewlet
from schooltool.skin.flourish.page import Page
from schooltool.skin.flourish.page import ModalFormLinkViewlet
from schooltool.skin.flourish.form import Form
from schooltool.skin.flourish.form import AddForm
from schooltool.skin.flourish.form import DialogForm
from schooltool.skin.flourish.form import DisplayForm
from schooltool.skin.flourish.viewlet import ViewletManager


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

    template = ViewPageTemplateFile('templates/f_groupsviewlet.pt')
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


class FlourishGroupFilterWidget(FilterWidget):

    template = ViewPageTemplateFile('templates/f_group_filter.pt')


class SchoolYearColumn(column.GetterColumn):

    def getter(self, item, formatter):
        schoolyear = ISchoolYear(item.__parent__)
        return schoolyear.title

    def getSortKey(self, item, formatter):
        schoolyear = ISchoolYear(item.__parent__)
        return schoolyear.first


class FlourishGroupTableFormatter(SchoolToolTableFormatter):

    def columns(self):
        title = LocaleAwareGetterColumn(
            name='title',
            title=_(u"Title"),
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(title, ISortableColumn)
        return [title]

    def render(self):
        formatter = self._table_formatter(
            self.context, self.request, self._items,
            columns=self._columns,
            batch_start=self.batch.start, batch_size=self.batch.size,
            sort_on=self._sort_on,
            prefix=self.prefix)
        formatter.cssClasses['table'] = 'groups-table relationships-table'
        return formatter()


class FlourishGroupListView(FlourishRelationshipViewBase):

    current_title = _('Current groups')
    available_title = _('Available groups')

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
        columns = super(FlourishGroupListView, self).getColumnsAfter(prefix)
        schoolyear = SchoolYearColumn(
            name='schoolyear',
            title=_(u'School Year'),
            subsort=True)
        directlyProvides(schoolyear, ISortableColumn)
        return [schoolyear] + columns

    def sortOn(self):
        return (('schoolyear', True), ("title", False))

    def setUpTables(self):
        self.available_table = self.createTableFormatter(
            ommit=self.getOmmitedItems(),
            items=self.getAvailableItems(),
            sort_on=self.sortOn(),
            prefix="add_item")
        self.selected_table = self.createTableFormatter(
            filter=lambda l: l,
            items=self.getSelectedItems(),
            sort_on=self.sortOn(),
            prefix="remove_item",
            batch_size=0)

    def getKey(self, item):
        schoolyear = ISchoolYear(item.__parent__)
        return "%s.%s" % (schoolyear.__name__, item.__name__)


class GroupsTertiaryNavigationManager(ViewletManager):

    template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)

    list_class = 'third-nav'

    @property
    def items(self):
        result = []
        schoolyears = ISchoolYearContainer(self.context)
        active = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            active = schoolyears.get(schoolyear_id, active)
        for schoolyear in schoolyears.values():
            url = '%s/%s?schoolyear_id=%s' % (
                absoluteURL(self.context, self.request),
                'groups',
                schoolyear.__name__)
            result.append({
                    'class': schoolyear.first == active.first and 'active' or None,
                    'viewlet': u'<a href="%s">%s</a>' % (url, schoolyear.title),
                    })
        return result


class GroupsAddLinks(RefineLinksViewlet):
    """Manager for Add links in GroupsView"""


class GroupLinks(RefineLinksViewlet):
    """Manager for public links in GroupView"""

    @property
    def title(self):
        return _("${group}'s", mapping={'group': self.context.title})


class GroupAddLinks(RefineLinksViewlet):
    """Manager for Add links in GroupView"""

    def render(self):
        # This check is necessary because the user can be a leader
        # of the context group, which gives him schooltool.edit on it
        if canAccess(self.context.__parent__, '__delitem__'):
            return super(GroupAddLinks, self).render()


class GroupManageActionsLinks(RefineLinksViewlet):
    """Manager for Action links in GroupView"""

    body_template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/renderable_items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)

    # We don't want this manager rendered at all
    # if there are no renderable viewlets
    @property
    def renderable_items(self):
        result = []
        for item in self.items:
            render_result = item['viewlet']()
            if render_result and render_result.strip():
                result.append({
                        'class': item['class'],
                        'viewlet': render_result,
                        })
        return result

    def render(self):
        # This check is necessary because the user can be a leader
        # of the context group, which gives him schooltool.edit on it
        if canAccess(self.context.__parent__, '__delitem__'):
            if self.renderable_items:
                return super(GroupManageActionsLinks, self).render()


class GroupDeleteLink(ModalFormLinkViewlet):

    @property
    def dialog_title(self):
        title = _(u'Delete ${group}',
                  mapping={'group': self.context.title})
        return translate(title, context=self.request)

    def render(self, *args, **kw):
        unwrapped = removeSecurityProxy(self.context)
        dependable = IDependable(unwrapped, None)
        if dependable is None or not bool(dependable.dependents()):
            return super(GroupDeleteLink, self).render(*args, **kw)


class GroupAddLinkViewlet(LinkViewlet):

    @property
    def schoolyear(self):
        schoolyears = ISchoolYearContainer(self.context)
        result = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            result = schoolyears.get(schoolyear_id, result)
        return result

    @property
    def url(self):
        groups = IGroupContainer(self.schoolyear)
        return '%s/%s' % (absoluteURL(groups, self.request),
                          'addSchoolToolGroup.html')

class GroupAddLinkFromGroupViewlet(GroupAddLinkViewlet):

    @property
    def schoolyear(self):
        return ISchoolYear(self.context.__parent__)

    @property
    def url(self):
        groups = IGroupContainer(self.schoolyear)
        return '%s/%s?camefrom=%s' % (
            absoluteURL(groups, self.request),
            'addSchoolToolGroup.html',
            absoluteURL(self.context, self.request))


class FlourishGroupsView(FlourishTableContainerView):

    content_template = ViewPageTemplateFile('templates/f_groups.pt')

    @property
    def title(self):
        schoolyear = self.schoolyear
        return _('Groups for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})

    @property
    def schoolyear(self):
        schoolyears = ISchoolYearContainer(self.context)
        result = schoolyears.getActiveSchoolYear()
        if 'schoolyear_id' in self.request:
            schoolyear_id = self.request['schoolyear_id']
            result = schoolyears.get(schoolyear_id, result)
        return result

    @property
    def container(self):
        schoolyear = self.schoolyear
        return IGroupContainer(schoolyear)

    def getColumnsAfter(self):
        description = column.GetterColumn(
            name='description',
            title=_('Description'),
            getter=lambda i, f: i.description or '',
            )
        return [description]


class FlourishGroupContainerDeleteView(ContainerDeleteView):

    def nextURL(self):
        if 'CONFIRM' in self.request:
            schoolyear = ISchoolYear(self.context)
            url = '%s/%s?schoolyear_id=%s' % (
                absoluteURL(ISchoolToolApplication(None), self.request),
                'groups',
                schoolyear.__name__)
            return url
        return ContainerDeleteView.nextURL(self)


class FlourishGroupView(DisplayForm):

    template = InheritTemplate(Page.template)
    content_template = ViewPageTemplateFile('templates/f_group_view.pt')
    fields = field.Fields(IGroup)
    fields = fields.select('title', 'description')

    @property
    def canModify(self):
        return checkPermission('schooltool.edit', self.context)

    @property
    def title(self):
        schoolyear = ISchoolYear(self.context.__parent__)
        return _('Groups for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})

    @property
    def subtitle(self):
        return self.context.title

    def done_link(self):
        schoolyear = ISchoolYear(self.context.__parent__)
        url = '%s/%s?schoolyear_id=%s' % (
            absoluteURL(ISchoolToolApplication(None), self.request),
            'groups',
            schoolyear.__name__)
        return url

    def updateWidgets(self):
        super(FlourishGroupView, self).updateWidgets()
        for widget in self.widgets.values():
            if not widget.value:
                widget.mode = HIDDEN_MODE

    # XXX: GroupView.getPersons uses canAccess on the member title
    #      should we do the same here?
    @property
    def members_table(self):
        return self.getTable(list(self.context.members))

    def has_members(self):
        return bool(list(self.context.members))

    # XXX: leaders logic, duplicated from FlourishBaseResourceView

    @property
    def leaders_table(self):
        return self.getTable(list(self.context.leaders))

    def getTable(self, items):
        persons = ISchoolToolApplication(None)['persons']
        result = getMultiAdapter((persons, self.request), ITableFormatter)
        result.setUp(table_formatter=table.StandaloneFullFormatter, items=items)
        return result

    def has_leaders(self):
        return bool(list(self.context.leaders))


class FlourishGroupAddView(AddForm):

    template = InheritTemplate(Page.template)
    label = None
    legend = _('Group Information')
    fields = field.Fields(IGroup)
    fields = fields.select('title', 'description')

    def updateActions(self):
        super(FlourishGroupAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @button.buttonAndHandler(_('Add'))
    def handleAdd(self, action):
        super(FlourishGroupAddView, self).handleAdd.func(self, action)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        if 'camefrom' in self.request:
            url = self.request['camefrom']
            self.request.response.redirect(url)
            return
        schoolyear = ISchoolYear(self.context)
        url = '%s/%s?schoolyear_id=%s' % (
            absoluteURL(ISchoolToolApplication(None), self.request),
            'groups',
            schoolyear.__name__)
        self.request.response.redirect(url)

    def create(self, data):
        group = Group(data['title'], data.get('description'))
        form.applyChanges(self, group, data)
        return group

    def add(self, group):
        chooser = INameChooser(self.context)
        name = chooser.chooseName(u'', group)
        self.context[name] = group
        self._group = group
        return group

    def nextURL(self):
        return absoluteURL(self._group, self.request)

    @property
    def title(self):
        schoolyear = ISchoolYear(self.context)
        return _('Groups for ${schoolyear}',
                 mapping={'schoolyear': schoolyear.title})


class FlourishGroupEditView(Form, form.EditForm):

    template = InheritTemplate(Page.template)
    label = None
    legend = _('Group Information')
    fields = field.Fields(IGroup)
    fields = fields.select('title', 'description')

    @property
    def title(self):
        return self.context.title

    def update(self):
        return form.EditForm.update(self)

    @button.buttonAndHandler(_('Submit'), name='apply')
    def handleApply(self, action):
        super(FlourishGroupEditView, self).handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class FlourishGroupDeleteView(DialogForm, form.EditForm):
    """View used for confirming deletion of a group."""

    dialog_submit_actions = ('apply',)
    dialog_close_actions = ('cancel',)
    label = None

    def updateDialog(self):
        # XXX: fix the width of dialog content in css
        if self.ajax_settings['dialog'] != 'close':
            self.ajax_settings['dialog']['width'] = 544 + 16

    @button.buttonAndHandler(_("Delete"), name='apply')
    def handleDelete(self, action):
        url = '%s/delete.html?delete.%s&CONFIRM' % (
            absoluteURL(self.context.__parent__, self.request),
            self.context.__name__)
        self.request.response.redirect(url)
        # We never have errors, so just close the dialog.
        self.ajax_settings['dialog'] = 'close'

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        pass

    def updateActions(self):
        super(FlourishGroupDeleteView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class FlourishMemberViewPersons(FlourishRelationshipViewBase):
    """View class for adding / removing members to / from a group."""

    @property
    def title(self):
        return self.context.title

    current_title = _("Current members")
    available_title = _("Add members")

    def getSelectedItems(self):
        """Return a list of current group memebers."""
        return filter(IPerson.providedBy, self.context.members)

    def getAvailableItemsContainer(self):
        return ISchoolToolApplication(None)['persons']

    def getCollection(self):
        return self.context.members
