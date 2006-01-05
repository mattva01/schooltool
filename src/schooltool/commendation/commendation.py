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
from zope.app import annotation
from zope.app.container import btree, contained
from schooltool.app import app
from schooltool.commendation import interfaces

# Annoations are identified using annotation keys that must be truly
# unique. Thus it is a good idea to make the Python path of the pacakge the
# prefix of the annotation key. Below are the two keys we need.
CommendationsKey = 'schooltool.commendation.Commendations'
CommendationsCacheKey = 'schooltool.commendation.Cache'

class Commendation(persistent.Persistent, contained.Contained):
    """A simple commendation implementation."""

    zope.interface.implements(interfaces.ICommendation,
                              interfaces.ICommendationContained)

    # We are using ``FieldProperty`` properties to implement the data
    # fields. ``FieldProperty`` isntances ensure that no invalid values are
    # assigned to the attribute.
    title = fieldproperty.FieldProperty(interfaces.ICommendation['title'])

    description = fieldproperty.FieldProperty(
        interfaces.ICommendation['description'])

    scope = fieldproperty.FieldProperty(interfaces.ICommendation['scope'])

    date = fieldproperty.FieldProperty(interfaces.ICommendation['date'])

    grantor = fieldproperty.FieldProperty(interfaces.ICommendation['grantor'])

    def __init__(self, title, description, scope):
        self.date = datetime.date.today()
        # Extract the current principal's id. If no interaction is found, then
        # we also do not have a user. Thus we simply store a special string
        # stating that the user was not found.
        interaction = zope.security.management.queryInteraction()
        if interaction and interaction.participations:
            self.grantor = interaction.participations[0].principal.id
        else:
            self.grantor = u'<unknown>'
        self.title = title
        self.description = description
        self.scope = scope

    def __repr__(self):
        # Providing an alternative implementation of the object's
        # representation is commonly helpful, especially for doctests.
        return '<%s %r by %r>' %(self.__class__.__name__,
                                 self.title, self.grantor)


class Commendations(btree.BTreeContainer):
    '''A simple implementation of ``ICommendations``.'''
    zope.interface.implements(interfaces.ICommendations)

    def __repr__(self):
        return '<%s for %r>' %(self.__class__.__name__, self.__parent__)


def getCommendations(context):
    """Adapt an ``IHaveCommendations`` object to ``ICommendations``."""
    annotations = annotation.interfaces.IAnnotations(context)
    try:
        return annotations[CommendationsKey]
    except KeyError:
        # If the key was not found, then we have never added it, so do that
        # now. Make sure that the annotation has a valid parent, so that we
        # can create URLs and do local component lookups.
        annotations[CommendationsKey] = Commendations()
        annotations[CommendationsKey].__parent__ = context
        return annotations[CommendationsKey]


def cacheCommendation(commendation, event):
    """Cache a newly created commendation."""
    # Whereever we are, get the SchoolTool application and access its
    # annotations. Then add the commendation to the list of all cached
    # commendations.
    stapp = app.getSchoolToolApplication()
    annotations = annotation.interfaces.IAnnotations(stapp)
    if CommendationsCacheKey not in annotations:
        annotations[CommendationsCacheKey] = persistent.list.PersistentList()
    annotations[CommendationsCacheKey].append(commendation)
