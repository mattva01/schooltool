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

from zope.interface import implements

from schooltool.interfaces import ISchoolToolApplication
from schooltool.interfaces import ICourse, ISection
from schoolbell.app.app import SchoolBellApplication, Group

class SchoolToolApplication(SchoolBellApplication):
    """The main SchoolTool application object"""

    implements(ISchoolToolApplication)

    def __init__(self):
        SchoolBellApplication.__init__(self)
        self['groups']['teachers'] = Group('teachers', 'Teaching Staff')
        self['groups']['students'] = Group('students', 'Students')
        self['groups']['courses'] = Group('courses',
                                          'Courses currently offered')


class Course(Group):

    implements(ICourse)

class Section(Group):

    implements(ISection)
