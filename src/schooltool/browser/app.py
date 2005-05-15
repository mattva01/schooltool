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
from zope.app.container.traversal import ContainerTraverser
from zope.security.proxy import removeSecurityProxy
from zope.publisher.interfaces.browser import IBrowserPublisher

from schooltool.interfaces import ISchoolToolApplication
from schooltool.interfaces import ICourseContainer, ISectionContainer
from schoolbell.app.browser.app import GroupView, ContainerView
from schoolbell.app.browser import app as sb
from schoolbell.app.interfaces import ISchoolBellApplication

from schooltool import SchoolToolMessageID as _
from schooltool.interfaces import ICourse, ISection
from schooltool.interfaces import IPersonPreferences
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


class SectionContainerView(ContainerView):
    """A Course Container view."""

    __used_for__ = ISectionContainer

    index_title = _("Section index")
    add_title = _("Add a new section")
    add_url = "+/addSchoolToolSection.html"


class SectionView(BrowserView):
    """A view for courses providing a list of sections."""

    __used_for__ = ISection


class SectionAddView(AddView):
    """A view for adding Sections."""

    error = None
    course = None

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


class PersonAddView(sb.PersonAddView):
    """An add view that creates SchoolTool, rather than SchoolBell, persons"""

    _factory = Person


class PersonPreferencesView(sb.PersonPreferencesView):
    """View used for editing person preferences."""

    __used_for__ = IPersonPreferences

    schema = IPersonPreferences
