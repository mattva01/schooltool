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

$Id$
"""
from persistent import Persistent
import zope.interface

from zope.interface import implementer
from zope.component import adapts
from zope.component import adapter
from zope.component import getUtility
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.app.intid import addIntIdSubscriber
from zope.app.intid.interfaces import IIntIds
from zope.app.container.contained import ObjectAddedEvent
from zope.app.container.interfaces import IObjectAddedEvent
from zope.app.container import btree, contained

from schooltool.term.interfaces import ITerm
from schooltool.schoolyear.subscriber import ObjectEventAdapterSubscriber
from schooltool.schoolyear.interfaces import ISchoolYearContainer
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.relationship import RelationshipProperty
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.app import InitBase
from schooltool.app import relationships
from schooltool.app.app import Asset
from schooltool.course.interfaces import ICourse
from schooltool.course.interfaces import ICourseContainer
from schooltool.course import interfaces


class CourseContainerContainer(btree.BTreeContainer):
    """Container of Courses."""

    zope.interface.implements(interfaces.ICourseContainerContainer,
                              IAttributeAnnotatable)


class CourseContainer(btree.BTreeContainer):
    """Container of Courses."""

    zope.interface.implements(interfaces.ICourseContainer,
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
    addIntIdSubscriber(sy, ObjectAddedEvent(sy))
    int_ids = getUtility(IIntIds)
    sy_id = str(int_ids.getId(sy))
    app = ISchoolToolApplication(None)
    cc = app['schooltool.course.course'].get(sy_id, None)
    if cc is None:
        cc = app['schooltool.course.course'][sy_id] = CourseContainer()
    return cc


@adapter(ITerm)
@implementer(ICourseContainer)
def getCourseContainerForTerm(term):
    return ICourseContainer(ISchoolYear(term))


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


class Course(Persistent, contained.Contained, Asset):

    zope.interface.implements(interfaces.ICourseContained,
                              IAttributeAnnotatable)

    sections = RelationshipProperty(relationships.URICourseSections,
                                    relationships.URICourse,
                                    relationships.URISectionOfCourse)

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description


class CourseInit(InitBase):

    def __call__(self):
        self.app['schooltool.course.course'] = CourseContainerContainer()


class InitCoursesForNewSchoolYear(ObjectEventAdapterSubscriber):
    adapts(IObjectAddedEvent, ISchoolYear)

    def copyAllCourses(self, source, destination):
        for id, course in source.items():
            new_course = destination[course.__name__] = Course(course.title,
                                                               course.description)

    def __call__(self):
        app = ISchoolToolApplication(None)
        syc = ISchoolYearContainer(app)
        active_schoolyear = syc.getActiveSchoolYear()

        if active_schoolyear is not None:
            self.copyAllCourses(ICourseContainer(active_schoolyear),
                                ICourseContainer(self.object))
