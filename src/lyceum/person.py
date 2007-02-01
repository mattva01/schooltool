#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Lyceum person specific code.

$Id$

"""
from zope.interface import implements
from zope.component import adapts
from zope.interface import directlyProvides
from zope.interface import Interface

from zc.table.interfaces import ISortableColumn

from schooltool.person.person import Person
from schooltool.person.interfaces import IPersonFactory
from schooltool.course.section import PersonInstructorsCrowd
from schooltool.person.person import PersonCalendarCrowd
from schooltool.skin.table import LocaleAwareGetterColumn
from lyceum import LyceumMessage as _


class ILyceumPerson(Interface):
    """Marker interface for Lyceum specific person."""


class LyceumPerson(Person):
    implements(ILyceumPerson)


class PersonFactoryUtility(object):

    implements(IPersonFactory)

    def columns(self):
        title = LocaleAwareGetterColumn(
            name='title',
            title=_(u'Full Name'),
            getter=lambda i, f: i.title,
            subsort=True)
        directlyProvides(title, ISortableColumn)

        return [title]

    def sortOn(self):
        return (("title", False),)

    def groupBy(self):
        return (("grade", False),)

    def __call__(self, *args, **kw):
        result = LyceumPerson(*args, **kw)
        return result


class LyceumPersonCalendarCrowd(PersonCalendarCrowd):
    """Crowd that allows instructor of a person access persons calendar"""
    adapts(ILyceumPerson)

    def contains(self, principal):
        return (PersonCalendarCrowd.contains(self, principal) or
                PersonInstructorsCrowd(self.context).contains(principal))
