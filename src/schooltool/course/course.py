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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Course implementation
"""

from persistent import Persistent

from zope.interface import implementer
from zope.interface import implements
from zope.component import adapts
from zope.component import adapter
from zope.component import getUtility
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.container.contained import Contained
from zope.container.btree import BTreeContainer

from schooltool.term.interfaces import ITerm
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.relationship import RelationshipProperty
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.app import InitBase
from schooltool.app import relationships
from schooltool.app.app import Asset
from schooltool.level import level
from schooltool.course.interfaces import ICourse
from schooltool.course.interfaces import ICourseContainer
from schooltool.course import interfaces


COURSE_CONTAINER_KEY = 'schooltool.course.course'


class CourseContainerContainer(BTreeContainer):
    """Container of Courses."""

    implements(interfaces.ICourseContainerContainer,
                              IAttributeAnnotatable)


class CourseContainer(BTreeContainer):
    """Container of Courses."""

    implements(interfaces.ICourseContainer,
                              IAttributeAnnotatable)


@adapter(ISchoolToolApplication)
@implementer(ICourseContainer)
def getCourseContainerForApp(app):
    syc = ISchoolYearContainer(app)
    sy = syc.getActiveSchoolYear()
    if sy is not None:
        return ICourseContainer(sy)


@adapter(ISchoolYear)
@implementer(ICourseContainer)
def getCourseContainer(sy):
    int_ids = getUtility(IIntIds)
    sy_id = str(int_ids.getId(sy))
    app = ISchoolToolApplication(None)
    cc = app[COURSE_CONTAINER_KEY].get(sy_id, None)
    if cc is None:
        cc = app[COURSE_CONTAINER_KEY][sy_id] = CourseContainer()
    return cc


@adapter(ITerm)
@implementer(ICourseContainer)
def getCourseContainerForTerm(term):
    return ICourseContainer(ISchoolYear(term))


@adapter(ICourse)
@implementer(ICourseContainer)
def getCourseContainerForCourse(course):
    return course.__parent__


@adapter(ICourseContainer)
@implementer(ISchoolYear)
def getSchoolYearForCourseContainer(course_container):
    container_id = int(course_container.__name__)
    int_ids = getUtility(IIntIds)
    container = int_ids.getObject(container_id)
    return container


@adapter(ICourse)
@implementer(ISchoolYear)
def getSchoolYearForCourse(course):
    return ISchoolYear(course.__parent__)


class Course(Persistent, Contained, Asset):

    implements(interfaces.ICourseContained, IAttributeAnnotatable)

    sections = RelationshipProperty(relationships.URICourseSections,
                                    relationships.URICourse,
                                    relationships.URISectionOfCourse)

    levels = RelationshipProperty(level.URILevelCourses,
                                  level.URICourse,
                                  level.URILevel)

    course_id = None
    government_id = None
    credits = None

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description


class CourseInit(InitBase):

    def __call__(self):
        self.app[COURSE_CONTAINER_KEY] = CourseContainerContainer()


class RemoveCoursesWhenSchoolYearIsDeleted(ObjectEventAdapterSubscriber):
    adapts(IObjectRemovedEvent, ISchoolYear)

    def __call__(self):
        course_container = ICourseContainer(self.object)
        for course_id in list(course_container.keys()):
            del course_container[course_id]
        del course_container.__parent__[course_container.__name__]
