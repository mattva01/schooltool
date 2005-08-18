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
Person Details implementation

$Id:$
"""
from persistent import Persistent
from zope.interface import implements
from zope.app.annotation.interfaces import IAnnotations

from schoolbell.app.person import interfaces

class PersonDetails(Persistent):

    implements(interfaces.IPersonDetails)

    __name__ = 'details'

    def __init__(self, nickname=None, primary_email=None,
                 secondary_email=None, primary_phone=None,
                 secondary_phone=None, mailing_address=None, home_page=None):
        self.nickname = nickname
        self.primary_email = primary_email
        self.secondary_email = secondary_email
        self.primary_phone = primary_phone
        self.secondary_phone = secondary_phone
        self.mailing_address = mailing_address
        self.home_page = home_page


def getPersonDetails(person):
    """Adapt an IPerson object to IPersonDetails."""
    annotations = IAnnotations(person)
    key = 'schoolbell.app.PersonDetails'
    try:
        return annotations[key]
    except KeyError:
        annotations[key] = PersonDetails()
        annotations[key].__parent__ = person
        return annotations[key]
