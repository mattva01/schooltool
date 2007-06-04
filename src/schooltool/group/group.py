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

$Id$
"""
__docformat__ = 'restructuredtext'
from persistent import Persistent

from zope.interface import implements
from zope.component import adapts
from zope.component import getAdapter
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.dependable.interfaces import IDependable
from zope.app.container import btree
from zope.app.container.contained import Contained
from zope.app.catalog.interfaces import ICatalog
from zope.app.catalog.catalog import Catalog
from zope.component import getUtility

from zc.catalog.catalogindex import ValueIndex

from schooltool.app.app import InitBase
from schooltool.app.interfaces import ICalendarParentCrowd
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.membership import GroupMemberCrowd
from schooltool.app.membership import URIMembership, URIMember, URIGroup
from schooltool.app.relationships import URIInstruction
from schooltool.app.relationships import URISection
from schooltool.app.security import ConfigurableCrowd
from schooltool.app.security import LeaderCrowd
from schooltool.group import interfaces
from schooltool.person.interfaces import IPerson
from schooltool.relationship import RelationshipProperty
from schooltool.relationship.relationship import getRelatedObjects
from schooltool.securitypolicy.crowds import Crowd
from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
from schooltool.securitypolicy.interfaces import ICrowd
from schooltool.group.interfaces import IGroup
from schooltool.utility.utility import UtilitySetUp


GROUP_CATALOG_KEY = 'schooltool.group'


class GroupContainer(btree.BTreeContainer):
    """Container of groups."""

    implements(interfaces.IGroupContainer, IAttributeAnnotatable)


from schooltool.app.app import Asset
class Group(Persistent, Contained, Asset):
    """Group."""

    implements(interfaces.IGroup, interfaces.IGroupContained,
               IAttributeAnnotatable)

    members = RelationshipProperty(URIMembership, URIGroup, URIMember)

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description


class GroupInit(InitBase):

    def __call__(self):
        self.app['groups'] = GroupContainer()
        default_groups =  [
            ("manager",        "Site Managers",         "Manager Group."),
            ("students",       "Students",              "Students."),
            ("teachers",       "Teachers",              "Teachers."),
            ("clerks",         "Clerks",                "Clerks."),
            ("administrators", "School Administrators", "School Administrators."),
            ]
        for id, title, description in default_groups:
            group = self.app['groups'][id] = Group(title, description)
            IDependable(group).addDependent('')


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


def catalogSetUp(catalog):
    catalog['__name__'] = ValueIndex('__name__', IGroup)
    catalog['title'] = ValueIndex('title', IGroup)


catalogSetUpSubscriber = UtilitySetUp(
    Catalog, ICatalog, GROUP_CATALOG_KEY, setUp=catalogSetUp)


def getGroupContainerCatalog(container):
    return getUtility(ICatalog, GROUP_CATALOG_KEY)
