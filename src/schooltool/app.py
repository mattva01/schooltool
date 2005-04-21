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

from schooltool.interfaces import ISchoolToolApplication
from schooltool.interfaces import ICourse, ISection
from schoolbell.app.app import SchoolBellApplication, Group


# XXX Should we use the Zope 3 translation service here?
localedir = os.path.join(os.path.dirname(__file__), 'locales')
catalog = gettext.translation('schooltool', localedir, fallback=True)
_ = lambda us: catalog.ugettext(us)


class SchoolToolApplication(SchoolBellApplication):
    """The main SchoolTool application object"""

    implements(ISchoolToolApplication)

    def __init__(self):
        SchoolBellApplication.__init__(self)
        # XXX Do we want to localize the container names?
        self['groups']['teachers'] = Group('teachers', _('Teaching Staff'))
        self['groups']['students'] = Group('students', _('Students'))
        self['groups']['courses'] = Group('courses',
                                          _('Courses currently offered'))


class Course(Group):

    implements(ICourse)

class Section(Group):

    implements(ISection)

    def __init__(self, title=None, description=None, teachers=None,
                 students=None, schedule=None, courses=None):
        Group.__init__(self)
        self.teachers = teachers
        self.students = students
        self.schedule = schedule
        self.courses = courses
