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
# Setting this attribute on the module declares that all doc strings in this
# module are written in restructured text, the default Python documentation
# format.
__docformat__ = 'reStructuredText'

import zope.interface
import zope.schema
import zope.i18nmessageid
from zope.app import container

# Since Zope 3 is an application server and does not know the users locale
# until a request is issued, we can only mark all strings that are supposed to
# be translated when displayed. Additionally, a translatable string must be
# assigned to a domain, so we know where it belongs to adn it allows us to
# disambiguate translations.
# In order for the string extraction tools to find the translatable strings,
# they have to be wrapped by ``_()``, namely a callable called ``_``
# (underscore).
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


# The ``IContainer`` interface specifes many methods that are related to
# component management. It basically implements the Python mapping
# API. However, its methods have to do a little bit more work, so that it
# integrates nicely into the Zope 3 framework.
class ICommendations(zope.app.container.interfaces.IContainer):
    '''An object containing several commendations.'''
    container.constraints.contains(ICommendation)

# ``IContained`` says that this object can be contained by another. Basically,
# it requires an object to provide a ``__parent__`` and ``__name__`` attribute.
class ICommendationContained(container.interfaces.IContained):
    '''A commendation that can only be contained by ``ICommendations``.'''
    container.constraints.containers(ICommendations)


class IHaveCommendations(zope.interface.Interface):
    '''Objects having commendations associated with them.'''
