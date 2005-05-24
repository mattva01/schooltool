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
SchoolTool application views.

$Id: app.py 3481 2005-04-21 15:28:29Z bskahan $
"""

from zope.app.publisher.browser import BrowserView
from zope.app.form.browser.add import AddView
from zope.app import zapi
from zope.app.component.hooks import getSite
from zope.app.form.utility import setUpWidgets, getWidgetsData
from zope.app.form.interfaces import IInputWidget, WidgetsError
from zope.security.proxy import removeSecurityProxy
from zope.publisher.interfaces.browser import IBrowserPublisher

from schoolbell.app.browser.app import GroupView, ContainerView
from schoolbell.app.browser import app as sb
from schoolbell.app.membership import URIMembership, URIGroup
from schoolbell.app.membership import isTransitiveMember
from schoolbell.app.interfaces import ISchoolBellApplication
from schoolbell.relationship import getRelatedObjects
from schoolbell.relationship.interfaces import IRelationshipLinks

from schooltool import SchoolToolMessageID as _
from schooltool.interfaces import ISchoolToolApplication
from schooltool.interfaces import ICourseContainer, ISectionContainer
from schooltool.interfaces import ICourse, ISection
from schooltool.interfaces import IPersonPreferences
from schooltool.interfaces import IGroup, IPerson, ISchoolToolApplication
from schooltool.relationships import URIInstruction, URIInstructor, URISection
from schooltool.app import Section, Person


class CourseContainerView(ContainerView):
    """A Course Container view."""

    __used_for__ = ICourseContainer

    index_title = _("Course index")
    add_title = _("Add a new course")
    add_url = "+/addSchoolToolCourse.html"


class CourseView(BrowserView):
    """A view for courses."""

    __used_for__ = ICourse


class CourseAddView(AddView):
    """A view for adding Courses."""

    def nextURL(self):
        return zapi.absoluteURL(self.context.context, self.request)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            return AddView.update(self)


class SectionContainerView(ContainerView):
    """A Course Container view."""

    __used_for__ = ISectionContainer

    index_title = _("Section index")
    add_title = _("Add a new section")
    add_url = "+/addSchoolToolSection.html"


class SectionView(BrowserView):
    """A view for courses providing a list of sections."""

    __used_for__ = ISection

    def getPersons(self):
        return filter(IPerson.providedBy, self.context.members)

    def getGroups(self):
        return filter(IGroup.providedBy, self.context.members)


class SectionAddView(AddView):
    """A view for adding Sections."""

    error = None
    course = None

    def validCourse(self):
        return self.course is not None

    def getCourseFromId(self, id):
        app = getSite()
        try:
            return app['courses'][id]
        except KeyError:
            self.error = _("No such course.")

    def __init__(self, context, request):
        super(AddView, self).__init__(context, request)

        try:
            course_id = request['field.course_id']
        except KeyError:
            self.error = _("Need a course ID.")
            return

        self.course = self.getCourseFromId(course_id)
        if self.course is not None:
            self.label = _("Add a Section to ${course}")
            self.label.mapping = {'course': self.course.title}

    def update(self):
        if self.update_status is not None:
            # We've been called before. Just return the previous result.
            return self.update_status

        if "UPDATE_SUBMIT" in self.request:
            self.update_status = ''
            try:
                data = getWidgetsData(self, self.schema, names=self.fieldNames)
                section = removeSecurityProxy(self.createAndAdd(data))
                self.course.sections.add(section)
            except WidgetsError, errors:
                self.errors = errors
                self.update_status = _("An error occured.")
                return self.update_status

            self.request.response.redirect(self.nextURL())

        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.course, self.request)
            self.request.response.redirect(url)

        return self.update_status

    def nextURL(self):
        return zapi.absoluteURL(self.course, self.request)


class SectionInstructorView(BrowserView):
    """View for adding instructors to a Section."""

    __used_for__ = ISection

    def getPotentialInstructors(self):
        """Return a list of all possible members."""
        container = ISchoolBellApplication(self.context)['persons']
        return container.values()

    def update(self):
        # This method is rather similar to GroupListView.update().
        context_url = zapi.absoluteURL(self.context, self.request)
        if 'UPDATE_SUBMIT' in self.request:
            context_instructors = removeSecurityProxy(self.context.instructors)
            for instructor in self.getPotentialInstructors():
                want = bool('instructor.' + instructor.__name__ in self.request)
                have = bool(instructor in context_instructors)
                # add() and remove() could throw an exception, but at the
                # moment the constraints are never violated, so we ignore
                # the problem.
                if want != have:
                    instructor = removeSecurityProxy(instructor)
                    if want:
                        context_instructors.add(instructor)
                    else:
                        context_instructors.remove(instructor)
            self.request.response.redirect(context_url)
        elif 'CANCEL' in self.request:
            self.request.response.redirect(context_url)


class SectionLearnerView(BrowserView):
    """View for adding learners to a Section.  """

    __used_for__ = ISection

    def getPotentialLearners(self):
        """Return a list of all possible members."""
        container = ISchoolBellApplication(self.context)['persons']
        return container.values()

    def update(self):
        # This method is rather similar to GroupListView.update().
        context_url = zapi.absoluteURL(self.context, self.request)
        if 'UPDATE_SUBMIT' in self.request:
            context_members = removeSecurityProxy(self.context.members)
            for member in self.getPotentialLearners():
                want = bool('member.' + member.__name__ in self.request)
                have = bool(member in context_members)
                # add() and remove() could throw an exception, but at the
                # moment the constraints are never violated, so we ignore
                # the problem.
                if want != have:
                    member = removeSecurityProxy(member)
                    if want:
                        context_members.add(member)
                    else:
                        context_members.remove(member)
            self.request.response.redirect(context_url)
        elif 'CANCEL' in self.request:
            self.request.response.redirect(context_url)


class SectionLearnerGroupView(SectionLearnerView):
    """View for adding groups of students to a Section."""

    def getPotentialLearners(self):
        """Return a list of all possible members."""
        container = ISchoolBellApplication(self.context)['groups']
        return container.values()


class PersonView(sb.PersonView):
    """Add additional information to the Person view.

    Tal friendly methods for determining if a person is a teacher or a
    student.
    """

    def isTeacher(self):
        links = IRelationshipLinks(self.context)

        if URIInstructor in [link.my_role for link in links]:
            return True
        else:
            return False

    def isLearner(self):
        for obj in getRelatedObjects(self.context, URIGroup,
                                     rel_type=URIMembership):
            if ISection.providedBy(obj):
                return True

        return False

    def instructorOf(self):
        return getRelatedObjects(self.context, URISection,
                                 rel_type=URIInstruction)

    def learnerOf(self):
        results = []
        sections = ISchoolBellApplication(self.context)['sections'].values()
        for section in sections:
            if isTransitiveMember(self.context, section):
                results.append(section)

        return results

    def memberOf(self):
        # this is a hack to get seperate out generic groups from sections
        results = []
        for group in self.context.groups:
            if not ISection.providedBy(group):
                results.append(group)

        return results


class PersonAddView(sb.PersonAddView):
    """An add view that creates SchoolTool, rather than SchoolBell, persons"""

    _factory = Person


class PersonPreferencesView(sb.PersonPreferencesView):
    """View used for editing person preferences."""

    __used_for__ = IPersonPreferences

    schema = IPersonPreferences
