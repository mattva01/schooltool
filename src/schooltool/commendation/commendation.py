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
"""Commendation Implementation

$Id$
"""
__docformat__ = 'reStructuredText'
import datetime
import persistent
import zope.interface
import zope.security
from zope.schema import fieldproperty
from schooltool.commendation import interfaces


class Commendation(persistent.Persistent):
    """A simple commendation implementation."""

    zope.interface.implements(interfaces.ICommendation)

    title = fieldproperty.FieldProperty(interfaces.ICommendation['title'])

    description = fieldproperty.FieldProperty(
        interfaces.ICommendation['description'])

    scope = fieldproperty.FieldProperty(interfaces.ICommendation['scope'])

    date = fieldproperty.FieldProperty(interfaces.ICommendation['date'])

    grantor = fieldproperty.FieldProperty(interfaces.ICommendation['grantor'])

    def __init__(self, title, description, scope):
        self.date = datetime.date.today()
        # Extract the current principal's id.
        interaction = zope.security.management.queryInteraction()
        if interaction and interaction.participations:
            self.grantor = interaction.participations[0].principal.id
        else:
            self.grantor = u'<unknown>'
        self.title = title
        self.description = description
        self.scope = scope

    def __repr__(self):
        return '<%s %r by %r>' %(self.__class__.__name__,
                                 self.title, self.grantor)
