#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003, 2004 Shuttleworth Foundation
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
Interfaces for authentication objects.

$Id$
"""

from zope.interface import Interface
from zope.schema import Object
from zope.schema import URI as URIField


# Tell i18nextractor that permission names are translatable
_ = lambda s: s

ViewPermission = _('View')
AddPermission = _('Add')
ModifyPermission = _('Modify')

Everybody = _('Everybody')

del _


class IACL(Interface):
    """Access control list.

    Access control lists store and manage tuples of (principal, permission).
    Permission can be one of View, Add, and Modify.
    """

    def __iter__():
        """Iterate over tuples of (principal, permission)."""

    def __contains__((principal,  permission)):
        """Return whether the principal, permission pair is in ACL."""

    def add((principal, permission)):
        """Grant the permission to a principal."""

    def remove((principal, permission)):
        """Revoke the permission from a principal.

        Raises KeyError if the principal does not have the permission.
        """

    def allows(principal, permission):
        """Return whether the principal has the permission.

        Contrary to __contains__, also returns True if the special
        principal Everybody has the permission.
        """

    def clear():
        """Remove all access from all principals"""


class IACLOwner(Interface):
    """An object that has an ACL."""

    acl = Object(
        title=u"The ACL for this calendar.",
        schema=IACL)
