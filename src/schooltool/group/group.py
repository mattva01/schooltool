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
from zope.app.securitypolicy.interfaces import IPrincipalRoleManager
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.dependable.interfaces import IDependable
from zope.app.container import btree
from zope.app.container.contained import Contained

from schooltool.relationship import RelationshipProperty
from schooltool.app.security import LeaderCrowd
from schooltool.securitypolicy.crowds import Crowd
from schooltool.securitypolicy.interfaces import ICrowd
from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
from schooltool.app.interfaces import ICalendarParentCrowd
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.membership import GroupMemberCrowd
from schooltool.app.membership import URIMembership, URIMember, URIGroup
from schooltool.app.security import ConfigurableCrowd
from schooltool.group import interfaces


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


def addGroupContainerToApplication(event):
    """Subscriber that adds a top-level groups container and a few groups."""
    app = event.object
    app['groups'] = GroupContainer()
    default_groups =  [
        ("manager",        "Site Managers",         "Manager Group."),
        ("students",       "Students",              "Students."),
        ("teachers",       "Teachers",              "Teachers."),
        ("clerks",         "Clerks",                "Clerks."),
        ("administrators", "School Administrators", "School Administrators."),
    ]
    for id, title, description in default_groups:
        group = app['groups'][id] = Group(title, description)
        IDependable(group).addDependent('')


class GroupContainerViewersCrowd(ConfigurableCrowd):
    setting_key = 'everyone_can_view_group_list'


class GroupViewersCrowd(ConfigurableCrowd):
    setting_key = 'everyone_can_view_group_info'


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
