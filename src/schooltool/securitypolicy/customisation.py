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
Customisation for SchoolTool security policy.
"""

from zope.interface import implements
from zope.annotation.interfaces import IAnnotations
from zope.component import subscribers
from persistent import Persistent
from persistent.dict import PersistentDict
from schooltool.securitypolicy.interfaces import IAccessControlCustomisations
from schooltool.securitypolicy.interfaces import IAccessControlSetting


class AccessControlCustomisations(Persistent):
    implements(IAccessControlCustomisations)

    def __init__(self):
        self._settings = PersistentDict()

    def getSetting(self, key):
        for setting in self:
            if setting.key == key:
                return setting
        else:
            raise KeyError("there is no AccessControlSetting"
                           " associated with this key.")

    def get(self, key):
        return self._settings.get(key, self.getSetting(key).default)

    def set(self, key, value):
        if self.getSetting(key):
            self._settings[key] = value

    def __iter__(self):
        settings = subscribers([None], IAccessControlSetting)
        return iter(settings)


def getAccessControlCustomisations(app):
    """Adapt a SchoolToolApplication to IAccessControlCustomisations."""

    annotations = IAnnotations(app)
    key = 'schooltool.securitypolicy.AccessControlCustomisations'
    try:
        return annotations[key]
    except KeyError:
        annotations[key] = AccessControlCustomisations()
        annotations[key].__parent__ = app
        return annotations[key]
