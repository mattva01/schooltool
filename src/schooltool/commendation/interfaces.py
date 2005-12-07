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
"""Commandation Interfaces

$Id$
"""
__docformat__ = 'reStructuredText'

import zope.interface
import zope.schema
import zope.i18nmessageid

_ = zope.i18nmessageid.MessageFactory("commendation")


class ICommendation(zope.interface.Interface):
    """A commendation (usually for a person or a group)."""

    title = zope.schema.TextLine(
        title=_("Title"),
        description=_("Title of the commendation."),
        required=True)

    description = zope.schema.Text(
        title=_("Description"),
        description=_("A detailed description of the commendation."),
        required=True)

    scope = zope.schema.Choice(
        title=_("Scope"),
        description=_("The scope of the commendation."),
        values=[_('group'), _('school-wide'), _('community'),
                _('state'), _('national'), _('global')],
        required=True)

    date = zope.schema.Date(
        title=_("Date"),
        description=_("The date the commendation was issued."),
        readonly=True,
        required=True)

    grantor = zope.schema.TextLine(
        title=_("Grantor"),
        description=_("The grantor of the commendation."),
        readonly=True,
        required=True)
