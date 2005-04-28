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

import os.path
import gettext
import locale
import locale

from zope.interface import implements
from zope.app.container.sample import SampleContainer

from schoolbell.relationship import RelationshipProperty
from schoolbell.app.app import SchoolBellApplication
from schoolbell.app.app import Group, GroupContainer
from schoolbell.app.app import PersonContainer, ResourceContainer
from schoolbell.app.cal import Calendar
from schoolbell.app.membership import URIMembership, URIGroup, URIMember
from schoolbell.app.app import SchoolBellApplication, Person, Group, Resource

from schooltool.interfaces import ISchoolToolApplication
from schooltool.interfaces import ISchoolToolGroupContainer
from schooltool.interfaces import ICourse, ISection
from schooltool.uris import URIInstruction, URISection, URIInstructor
from schooltool.uris import URILearning, URILearner
from schooltool.timetable import TermService, TimetableSchemaService

# XXX Should we use the Zope 3 translation service here?
localedir = os.path.join(os.path.dirname(__file__), 'locales')
catalog = gettext.translation('schooltool', localedir, fallback=True)
_ = lambda us: catalog.ugettext(us)


class SchoolToolApplication(SchoolBellApplication):
    """The main SchoolTool application object"""

    implements(ISchoolToolApplication)

    def __init__(self):
        SampleContainer.__init__(self)
        self['persons'] = PersonContainer()
        self['groups'] = groups = SchoolToolGroupContainer()
        self['resources'] = ResourceContainer()
        # XXX Do we want to localize the container names?
        groups['staff'] = Group('staff', _('Staff'))
        groups['learners'] = Group('learners', _('Learners'))
        groups['courses'] = Group('courses', _('Courses currently offered'))

        self.terms = TermService()
        self.timetableSchemaService = TimetableSchemaService()


class Course(Group):

    implements(ICourse)


class Section(Group):

    implements(ISection)

    def getLabel(self):
        label = ''
        for instructor in self.instructors:
            label = label + instructor.title + ' '
        label = label + _('section of ')
        for course in self.courses:
            label = label + course.title + ' '
        return label

    label = property(getLabel)

    def getTitle(self):
        courses = ''
        for course in self.courses:
            courses = courses + course.title + ' '

        return _('Section of ') + courses

    title = property(getTitle)

    instructors = RelationshipProperty(URIInstruction, URISection,
                                       URIInstructor)

    learners = RelationshipProperty(URILearning, URISection,
                                       URILearner)

    courses = RelationshipProperty(URIMembership, URIMember,
                                   URIGroup)



    def __init__(self, description=None, schedule=None,
                 courses=None):
        self.description = description
        self.schedule = schedule
        self.calendar = Calendar(self)


class SchoolToolGroupContainer(GroupContainer):
    """Extend the schoolbell group container to support subclasses."""

    implements(ISchoolToolGroupContainer)

