#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Interfaces for SchoolTool security policy.

"""

from zope.interface import Interface
from zope import schema
from zope.interface import Attribute
from zope.configuration.fields import PythonIdentifier
from zope.location.interfaces import IContained

from schooltool.common import SchoolToolMessage as _


class ICrowdsUtility(Interface):
    """Crowds Utility holds registered security information"""

    factories = schema.Dict(
        title=u"Crowd Factories",
        description=u"Maps crowd names to crowd factories")

    crowds = schema.Dict(
        title=u"Permission Crowds",
        description=u"Maps (permission, interface)s to crowd names")

    # TODO: update interface, it's out of date


class IDescriptionUtility(Interface):
    """Access rights description utility"""

    # TODO: describe fields


class ICrowd(Interface):
    """A crowd is conceptually a set of principals.

    A crowd need only support one operation -- a membership test.
    """

    title = schema.TextLine(title=u"Title", required=False)

    description = schema.Text(title=u"Description", required=False)

    def contains(principal):
        """Return True if principal is in the crowd."""


class IAccessControlCustomisations(Interface):
    """Access Control Customisation storage."""

    def get(key):
        """Return a value of a setting stored under the key."""

    def set(key, value):
        """Set the value of a setting stored under the key."""

    def __iter__():
        """Iterate through all customisation settings."""


class IAccessControlSetting(Interface):
    """An access control customisation setting."""

    key = PythonIdentifier(description=u"""A key that identified the setting.
                           For example: 'members_manage_groups',
                           'teachers_edit_person_info'
                           """)
    default = schema.Bool(title=u"The default value for the setting.")
    text = schema.TextLine(
        title=u"Description of the setting for the user interface.")
    alt_text = schema.TextLine(
        title=u"Description of the effect when the setting is off.")

    def getValue():
        """Return the value of the setting.

        Return the default if it is not set in the
        AccessControlCusomisations storage.
        """

    def setValue(value):
        """Set the value of the setting."""


class IDescription(IContained):
    """Base interface for a description object."""

    title = schema.TextLine(
        title=_("Title"),
        description=_("Title of the group."))

    description = schema.Text(
        title=_("Description"),
        required=False)


class IDescriptionGroup(IDescription):
    """A group of access descriptions."""


class IGroupAction(IDescription):
    """Actions that given permission enables on an object implementing
    given interface.
    """

    interface = Attribute(u"Interface")

    permission = schema.TextLine(
        title=u"Permission",
        required=True)


class ICrowdToDescribe(Interface):
    """Adapt to this interface to get the crowd to describe."""


class ICrowdDescription(IDescription):
    """Description of a crowd."""
