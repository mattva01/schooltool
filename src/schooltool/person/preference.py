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
Person Preferences implementation

$Id:$
"""
import calendar

from persistent import Persistent
from zope.interface import implements
from zope.app.annotation.interfaces import IAnnotations

from schooltool.person import interfaces

PERSON_PREFERENCES_KEY = 'schooltool.app.PersonPreferences'


class PersonPreferences(Persistent):

    implements(interfaces.IPersonPreferences)

    __parent__ = None

    timezone = "UTC"
    dateformat = "%Y-%m-%d"
    timeformat = "%H:%M"
    weekstart = calendar.MONDAY
    # XXX: Only available in schooltool, but that's okay for now.
    cal_periods = True


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
