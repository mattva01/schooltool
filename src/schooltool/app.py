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
SchoolTool application

$Id$
"""

from persistent import Persistent
from persistent.dict import PersistentDict
from zope.interface import implements
from zope.app.container.sample import SampleContainer
from zope.app.site.servicecontainer import SiteManagerContainer
from zope.app.annotation.interfaces import IAttributeAnnotatable

from schoolbell.relationship import RelationshipProperty
from schoolbell.app.cal import Calendar
from schoolbell.app.membership import URIMembership, URIGroup, URIMember
from schoolbell.app import app as sb

from schooltool import SchoolToolMessageID as _
from schooltool.interfaces import ISchoolToolApplication
from schooltool.interfaces import ISchoolToolGroupContainer
from schooltool.interfaces import ICourse, ISection
from schooltool.relationships import URIInstruction, URISection, URIInstructor
from schooltool.relationships import URILearning, URILearner
from schooltool.timetable import TermService, TimetableSchemaService
from schooltool.timetable import TimetabledMixin


class SchoolToolApplication(Persistent, SampleContainer, SiteManagerContainer):
    """The main SchoolTool application object"""

    implements(ISchoolToolApplication, IAttributeAnnotatable)

    def __init__(self):
        SampleContainer.__init__(self)
        self['persons'] = sb.PersonContainer()
        self['groups'] = groups = GroupContainer()
        self['resources'] = sb.ResourceContainer()
        groups['staff'] = Group('staff', _('Staff'))
        groups['learners'] = Group('learners', _('Learners'))
        groups['courses'] = Group('courses', _('Courses currently offered'))

        self.terms = TermService()
        self.terms.__parent__ = self
        self.terms.__name__ = 'terms'

        self.timetableSchemaService = TimetableSchemaService()

    def _newContainerData(self):
        return PersistentDict()


class Group(sb.Group, TimetabledMixin):

    def __init__(self, *args, **kw):
        sb.Group.__init__(self, *args, **kw)
        TimetabledMixin.__init__(self)


class Person(sb.Person, TimetabledMixin):

    def __init__(self, *args, **kw):
        sb.Person.__init__(self, *args, **kw)
        TimetabledMixin.__init__(self)


class Resource(sb.Resource, TimetabledMixin):

    def __init__(self, *args, **kw):
        sb.Resource.__init__(self, *args, **kw)
        TimetabledMixin.__init__(self)


class Course(Group):

    implements(ICourse)


class Section(Group):

    implements(ISection)

    def _getLabel(self):
        instructors = " ".join([i.title for i in self.instructors])
        courses = " ".join([c.title for c in self.courses])
        return _('%s section of %s') % (instructors, courses)

    label = property(_getLabel)

    def _getTitle(self):
        return _('Section of ') + " ".join([c.title for c in self.courses])

    title = property(_getTitle)

    instructors = RelationshipProperty(URIInstruction, URISection,
                                       URIInstructor)

    learners = RelationshipProperty(URILearning, URISection, URILearner)

    courses = RelationshipProperty(URIMembership, URIMember, URIGroup)

    def __init__(self, description=None, schedule=None, courses=None):
        self.description = description
        self.schedule = schedule
        self.calendar = Calendar(self)


class GroupContainer(sb.GroupContainer):
    """Extend the schoolbell group container to support subclasses."""

    implements(ISchoolToolGroupContainer)
