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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Person Preferences implementation
"""

from persistent import Persistent
from zope.interface import implements
from zope.annotation.interfaces import IAnnotations
from zope.location.location import ILocation

from schooltool.securitypolicy.crowds import OwnerCrowd
from schooltool.securitypolicy.crowds import ConfigurableCrowd
from schooltool.person import interfaces

PERSON_PREFERENCES_KEY = 'schooltool.app.PersonPreferences'


class PersonPreferences(Persistent):

    implements(interfaces.IPersonPreferences, ILocation)

    __name__ = 'preferences'
    __parent__ = None

    # XXX: Only available in schooltool, but that's okay for now.
    cal_periods = True
    cal_public = False


def getPersonPreferences(person):
    """Adapt an IAnnotatable object to IPersonPreferences."""
    annotations = IAnnotations(person)
    try:
        return annotations[PERSON_PREFERENCES_KEY]
    except KeyError:
        prefs = PersonPreferences()
        prefs.__parent__ = person
        annotations[PERSON_PREFERENCES_KEY] = prefs
        return prefs


def getPreferencesOwner(preferences):
    """Adapt IPersonPreferences to IPerson"""
    return interfaces.IPerson(preferences.__parent__)


class PersonPreferencesEditorsCrowd(ConfigurableCrowd):

    setting_key = 'persons_can_set_their_preferences'

    def contains(self, principal):
        """Return the value of the related setting (True or False)."""
        return (ConfigurableCrowd.contains(self, principal) and
                OwnerCrowd(self.context).contains(principal))
