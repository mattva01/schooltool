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

from schoolbell.app.app import SchoolBellApplication
from schoolbell.app.app import Group, GroupContainer
from schoolbell.app.app import PersonContainer, ResourceContainer
from schoolbell.app.cal import Calendar

from schooltool.interfaces import ISchoolToolApplication
from schooltool.interfaces import ISchoolToolGroupContainer
from schooltool.interfaces import ICourse, ISection
from schoolbell.app.app import SchoolBellApplication, Person, Group, Resource


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
        self['groups'] = SchoolToolGroupContainer()
        self['resources'] = ResourceContainer()
        # XXX Do we want to localize the container names?
        self['groups']['staff'] = Group('staff', _('Staff'))
        self['groups']['learners'] = Group('learners', _('Learners'))
        self['groups']['courses'] = Group('courses',
                                          _('Courses currently offered'))


class Course(Group):

    implements(ICourse)

class Section(Group):

    implements(ISection)

    def __init__(self, title=None, description=None, instructors=None,
                 learners=None, schedule=None, courses=None):
        self.title = title
        self.description = description
        self.instructors = instructors
        self.learners = learners
        self.schedule = schedule
        self.courses = courses
        self.calendar = Calendar(self)


class SchoolToolGroupContainer(GroupContainer):
    """Extend the schoolbell group container to support subclasses."""

    implements(ISchoolToolGroupContainer)
