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

from schoolbell.app.browser.app import GroupView
from schoolbell.app.browser.app import MemberViewBase

from schooltool import SchoolToolMessageID as _
from schooltool.interfaces import ICourse, ISection
from schooltool.interfaces import ISchoolBellApplication
from schooltool.app import Section

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
            self.label = 'Add a Section to ' + self.course.title

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

