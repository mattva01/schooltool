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
Course implementation

$Id: app.py 4750 2005-08-16 19:13:10Z srichter $
"""
from persistent import Persistent
import zope.interface

from zope.app.annotation.interfaces import IAttributeAnnotatable
from zope.app.container import btree, contained

from schooltool.relationship import RelationshipProperty
from schooltool import relationships
from schooltool.course import interfaces

class CourseContainer(btree.BTreeContainer):
    """Container of Courses."""

    zope.interface.implements(interfaces.ICourseContainer,
                              IAttributeAnnotatable)


class Course(Persistent, contained.Contained):

    zope.interface.implements(interfaces.ICourseContained,
                              IAttributeAnnotatable)

    sections = RelationshipProperty(relationships.URICourseSections,
                                    relationships.URICourse,
                                    relationships.URISectionOfCourse)

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description


def addCourseContainerToApplication(event):
    event.object['courses'] = CourseContainer()
