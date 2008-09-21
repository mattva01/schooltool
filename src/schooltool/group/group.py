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
from zope.app.container import btree
from zope.app.container.contained import Contained
from zope.app.container.contained import ObjectAddedEvent
from zope.app.container.interfaces import IObjectAddedEvent
from zope.app.dependable.interfaces import IDependable
from zope.app.intid import addIntIdSubscriber
from zope.app.intid.interfaces import IIntIds
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
from schooltool.app.relationships import URIInstruction
from schooltool.app.relationships import URISection
from schooltool.app.security import ConfigurableCrowd
from schooltool.app.security import LeaderCrowd
from schooltool.course.interfaces import ISection
from schooltool.group import interfaces
from schooltool.group.interfaces import IGroupContainer
from schooltool.person.interfaces import IPerson
from schooltool.relationship import RelationshipProperty
from schooltool.relationship.relationship import getRelatedObjects
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.securitypolicy.crowds import Crowd
from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
from schooltool.securitypolicy.interfaces import ICrowd


class GroupContainerContainer(btree.BTreeContainer):
    """Container of group containers."""

    implements(interfaces.IGroupContainerContainer,
               IAttributeAnnotatable)


class GroupContainer(btree.BTreeContainer):
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

    def initializeGroupContainer(self, groups):
        groups = IGroupContainer(self.object)
        default_groups =  [
            ("manager",        "Site Managers",         "Manager Group."),
            ("students",       "Students",              "Students."),
            ("teachers",       "Teachers",              "Teachers."),
            ("clerks",         "Clerks",                "Clerks."),
            ("administrators", "School Administrators", "School Administrators."),
            ]
        for id, title, description in default_groups:
            group = groups[id] = Group(title, description)
            IDependable(group).addDependent('')

    def copyMembers(self, group, new_group):
        for member in group.members:
            new_group.members.add(member)

    def copyAllGroups(self, source, destination):
        for id, group in source.items():
            new_group = destination[group.__name__] = Group(group.title, group.description)
            if id in ["managers", "teachers", "clerks", "administrators"]:
                self.copyMembers(group, new_group)

    def __call__(self):
        app = ISchoolToolApplication(None)
        syc = ISchoolYearContainer(app)
        active_schoolyear = syc.getActiveSchoolYear()

        if active_schoolyear:
            self.copyAllGroups(IGroupContainer(active_schoolyear),
                               IGroupContainer(self.object))
        else:
            self.initializeGroupContainer(IGroupContainer(self.object))


class GroupInit(InitBase):

    def __call__(self):
        self.app['schooltool.group'] = GroupContainerContainer()


class GroupContainerViewersCrowd(ConfigurableCrowd):
    setting_key = 'everyone_can_view_group_list'


class GroupViewersCrowd(ConfigurableCrowd):
    setting_key = 'everyone_can_view_group_info'


class GroupInstructorsCrowd(Crowd):
    implements(ICrowd)
    adapts(interfaces.IGroup)

    def contains(self, principal):
        person = IPerson(principal, None)
        if not person:
            return False
        person_sections = getRelatedObjects(person, URISection,
                                            rel_type=URIInstruction)
        group = self.context
        for section in person_sections:
            if group in section.members:
                return True
        return False


class GroupCalendarViewersCrowd(Crowd):
    implements(ICalendarParentCrowd)
    adapts(interfaces.IGroup)

    def contains(self, principal):
        """Return the value of the related setting (True or False)."""
        app = ISchoolToolApplication(None)
        customizations = IAccessControlCustomisations(app)
        setting = customizations.get('everyone_can_view_group_calendar')

        return (setting
                or GroupMemberCrowd(self.context).contains(principal)
                or LeaderCrowd(self.context).contains(principal))


class GroupCalendarEditorsCrowd(Crowd):
    implements(ICalendarParentCrowd)
    adapts(interfaces.IGroup)

    def contains(self, principal):
        """Return the value of the related setting (True or False)."""
        app = ISchoolToolApplication(None)
        customizations = IAccessControlCustomisations(app)
        setting = customizations.get('members_can_edit_group_calendar')
        if setting and GroupMemberCrowd(self.context).contains(principal):
            return True

        # Fall back to schooltool.edit for IGroup
        crowd = getAdapter(self.context, ICrowd, name='schooltool.edit')
        return crowd.contains(principal)
