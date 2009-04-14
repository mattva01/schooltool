#
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
Contact relationship views.
"""
from zope.security.proxy import removeSecurityProxy
from schooltool.person.interfaces import IPerson
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.browser.app import RelationshipViewBase

from schooltool.contact.interfaces import IContactable
from schooltool.contact.interfaces import IContactContainer
from schooltool.common import SchoolToolMessage as _


class ContactManagementView(RelationshipViewBase):
    """View class for adding/removing contacts to/from a person."""

    __used_for__ = IPerson

    current_title = _("Assigned Contacts")
    available_title = _("Available Contacts")

    @property
    def title(self):
        return _("Manage contacts of ${person}",
            mapping={'person': self.context.title})

    def getSelectedItems(self):
        return IContactable(self.context).contacts

    def getAvailableItemsContainer(self):
        return IContactContainer(ISchoolToolApplication(None))

    def getCollection(self):
        return IContactable(removeSecurityProxy(self.context)).contacts
