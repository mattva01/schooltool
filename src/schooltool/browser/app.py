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
from schoolbell.app.browser.app import GroupView
from schoolbell.app.browser import app as sb

from schooltool import SchoolToolMessageID as _
from schooltool.interfaces import ICourse, ISection
from schooltool.interfaces import ISchoolBellApplication
from schooltool.app import Section, Person

class CourseView(GroupView):
    """A view for courses providing a list of sections."""

    __used_for__ = ICourse

    def getSections(self):
        return self.context.members


class CourseAddView(AddView):
    "A view for adding Courses."


class SectionView(GroupView):
    """A view for courses providing a list of sections."""

    __used_for__ = ISection

    def getInstructors(self):
        return self.context.instructors

    def getLearners(self):
        return self.context.learners

    def getCourses(self):
        return self.context.courses


class SectionAddView(AddView):
    """A view for adding Sections."""

    error = None
    course = None

    def getCourseFromId(self, id):
        app = getSite()
        try:
            return app['groups'][id]
        except KeyError:
            self.error = _("No such course.")

    def __init__(self, context, request):

        super(AddView, self).__init__(context, request)

        try:
            self.course = self.getCourseFromId(request['field.course_id'])
        except KeyError:
            self.error = _("Need a course ID.")

        if self.course is not None:
            self.label = _('Add a Section to ') + self.course.title

    def update(self):

        if self.update_status is not None:
            # We've been called before. Just return the previous result.
            return self.update_status

        if "UPDATE_SUBMIT" in self.request:

            self.update_status = ''
            try:
                data = getWidgetsData(self, self.schema, names=self.fieldNames)
                section = removeSecurityProxy(self.createAndAdd(data))
                self.course.members.add(section)
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
            context_learners = removeSecurityProxy(self.context.learners)
            for learner in self.getPotentialLearners():
                want = bool('learner.' + learner.__name__ in self.request)
                have = bool(learner in context_learners)
                # add() and remove() could throw an exception, but at the
                # moment the constraints are never violated, so we ignore
                # the problem.
                if want != have:
                    learner = removeSecurityProxy(learner)
                    if want:
                        context_learners.add(learner)
                    else:
                        context_learners.remove(learner)
            self.request.response.redirect(context_url)
        elif 'CANCEL' in self.request:
            self.request.response.redirect(context_url)


class SchoolToolApplicationTraverser(ContainerTraverser):
    """URL traverser for ISchoolBellApplication"""

    __used_for__ = ISchoolToolApplication

    def publishTraverse(self, request, name):
        if name == 'terms':
            return self.context.terms
        else:
            return ContainerTraverser.publishTraverse(self, request, name)


class PersonAddView(sb.PersonAddView):
    """An add view that creates SchoolTool, rather than SchoolBell, persons"""

    _factory = Person
