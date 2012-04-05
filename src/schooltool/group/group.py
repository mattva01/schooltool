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
Group objects
"""
__docformat__ = 'restructuredtext'
from persistent import Persistent

from zope.annotation.interfaces import IAttributeAnnotatable
from zope.container.contained import Contained
from zope.container.btree import BTreeContainer
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent import ObjectAddedEvent
from zope.app.dependable.interfaces import IDependable
from zope.intid import addIntIdSubscriber
from zope.intid.interfaces import IIntIds
from zope.component import adapter
from zope.component import adapts
from zope.component import getAdapter
from zope.component import getUtility
from zope.interface import implementer
from zope.interface import implements

from schooltool.app.app import Asset
from schooltool.app.app import InitBase
from schooltool.app.interfaces import ICalendarParentCrowd
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.membership import GroupMemberCrowd
from schooltool.app.membership import URIMembership, URIMember, URIGroup
from schooltool.app.security import ConfigurableCrowd
from schooltool.app.security import LeaderCrowd
from schooltool.course.interfaces import ISection
from schooltool.group import interfaces
from schooltool.group.interfaces import IGroupContainer
from schooltool.relationship import RelationshipProperty
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.securitypolicy.crowds import Crowd, AggregateCrowd
from schooltool.securitypolicy.crowds import AggregateCrowdDescription
from schooltool.securitypolicy.metaconfigure import getCrowdsUtility
from schooltool.securitypolicy.interfaces import ICrowd
from schooltool.common import SchoolToolMessage as _


defaultGroups =  {"manager"       : _("Site Managers"),
                  "students"      : _("Students"),
                  "teachers"      : _("Teachers"),
                  "clerks"        : _("Clerks"),
                  "administrators": _("School Administrators"),
                  }


class GroupContainerContainer(BTreeContainer):
    """Container of group containers."""

    implements(interfaces.IGroupContainerContainer,
               IAttributeAnnotatable)


class GroupContainer(BTreeContainer):
    """Container of groups."""

    implements(interfaces.IGroupContainer, IAttributeAnnotatable)


@adapter(ISchoolYear)
@implementer(interfaces.IGroupContainer)
def getGroupContainer(sy):
    addIntIdSubscriber(sy, ObjectAddedEvent(sy))
    int_ids = getUtility(IIntIds)
    sy_id = str(int_ids.getId(sy))
    app = ISchoolToolApplication(None)
    gc = app['schooltool.group'].get(sy_id, None)
    if gc is None:
        gc = app['schooltool.group'][sy_id] = GroupContainer()
    return gc


@adapter(ISchoolToolApplication)
@implementer(interfaces.IGroupContainer)
def getGroupContainerForApp(app):
    syc = ISchoolYearContainer(app)
    sy = syc.getActiveSchoolYear()
    if sy is None:
        return None
    return IGroupContainer(sy)


@adapter(ISection)
@implementer(interfaces.IGroupContainer)
def getGroupContainerForSection(section):
    sy = ISchoolYear(section)
    return IGroupContainer(sy)


@adapter(interfaces.IGroupContainer)
@implementer(ISchoolYear)
def getSchoolYearForGroupContainer(group_container):
    container_id = int(group_container.__name__)
    int_ids = getUtility(IIntIds)
    container = int_ids.getObject(container_id)
    return container


class Group(Persistent, Contained, Asset):
    """Group."""

    implements(interfaces.IGroup, interfaces.IGroupContained,
               IAttributeAnnotatable)

    members = RelationshipProperty(URIMembership, URIGroup, URIMember)

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description


# XXX Unit test ME!
class InitGroupsForNewSchoolYear(ObjectEventAdapterSubscriber):

    adapts(IObjectAddedEvent, ISchoolYear)

    def initializeGroupContainer(self):
        groups = IGroupContainer(self.object)
        for id, title in defaultGroups.items():
            group = groups[id] = Group(title)
            IDependable(group).addDependent('')

    def importDefaultGroups(self, activeSchoolyear):
        oldGroups = IGroupContainer(activeSchoolyear)
        newGroups = IGroupContainer(self.object)
        for groupId in defaultGroups:
            if groupId in oldGroups:
                oldGroup = oldGroups[groupId]
                newGroup = Group(oldGroup.title, oldGroup.description)
                newGroups[groupId] = newGroup
                IDependable(newGroup).addDependent('')

    def __call__(self):
        app = ISchoolToolApplication(None)
        syc = ISchoolYearContainer(app)
        activeSchoolyear = syc.getActiveSchoolYear()
        if activeSchoolyear is not None:
            self.importDefaultGroups(activeSchoolyear)
        else:
            self.initializeGroupContainer()


class GroupInit(InitBase):

    def __call__(self):
        self.app['schooltool.group'] = GroupContainerContainer()


class GroupContainerViewersCrowd(ConfigurableCrowd):
    setting_key = 'everyone_can_view_group_list'


class GroupViewersCrowd(ConfigurableCrowd):
    setting_key = 'everyone_can_view_group_info'


class GroupCalendarSettingCrowd(ConfigurableCrowd):
    setting_key = 'everyone_can_view_group_calendar'


class GroupCalendarViewersCrowd(AggregateCrowd):
    implements(ICalendarParentCrowd)
    adapts(interfaces.IGroup)

    def crowdFactories(self):
        return [GroupCalendarSettingCrowd, GroupMemberCrowd, LeaderCrowd]


class GroupCalendarMemberSettingCrowd(ConfigurableCrowd):
    setting_key = 'members_can_edit_group_calendar'


class GroupCalendarEditorsCrowd(Crowd):
    implements(ICalendarParentCrowd)
    adapts(interfaces.IGroup)

    def contains(self, principal):
        """Return the value of the related setting (True or False)."""
        if (GroupCalendarMemberSettingCrowd(self.context).contains(principal) and
            GroupMemberCrowd(self.context).contains(principal)):
            return True

        # Fall back to schooltool.edit for IGroup
        crowd = getAdapter(self.context, ICrowd, name='schooltool.edit')
        return crowd.contains(principal)


class GroupCalendarEditorsCrowdDescription(AggregateCrowdDescription):

    def getFactories(self):
        crowd_util = getCrowdsUtility()
        crowds = crowd_util.getFactories('schooltool.edit', interfaces.IGroup)
        return [GroupCalendarMemberSettingCrowd] + crowds


class RemoveGroupsWhenSchoolYearIsDeleted(ObjectEventAdapterSubscriber):
    adapts(IObjectRemovedEvent, ISchoolYear)

    def __call__(self):
        group_container = IGroupContainer(self.object)
        for group_id, group in list(group_container.items()):
            IDependable(group).removeDependent('')
            del group_container[group_id]
