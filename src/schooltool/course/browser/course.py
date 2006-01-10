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
course browser views.

$Id: app.py 4691 2005-08-12 18:59:44Z srichter $
"""
from zope.app import zapi
from zope.app.form.browser.add import AddView
from zope.app.publisher.browser import BrowserView
from schooltool.app.browser.app import ContainerView

from schooltool import SchoolToolMessage as _
from schooltool.course.interfaces import ICourse, ICourseContainer, ISection
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.relationships import URIInstruction, URISection
from schooltool.relationship import getRelatedObjects
from schooltool.person.interfaces import IPerson

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

class CoursesViewlet(BrowserView):
    """A viewlet showing the courses a person is in."""

    def isTeacher(self):
        """Find out if the person is an instructor for any sections."""
        if len(getRelatedObjects(self.context, URISection,
                                 rel_type=URIInstruction)) > 0:
            return True
        else:
            return False

    def isLearner(self):
        """Find out if the person is a member of any sections."""
        for obj in self.context.groups:
            if ISection.providedBy(obj):
                return True

        return False

    def instructorOf(self):
        """Get the sections the person instructs."""
        return getRelatedObjects(self.context, URISection,
                                 rel_type=URIInstruction)

    def memberOf(self):
        """Seperate out generic groups from sections."""

        return [group for group in self.context.groups if not
                ISection.providedBy(group)]

    def learnerOf(self):
        """Get the sections the person is a member of."""
        results = []
        sections = getSchoolToolApplication()['sections'].values()
        for section in sections:
            if self.context in section.members:
                results.append({'section': section, 'group': None})
            # XXX isTransitiveMember works in the test fixture but not in the
            # application, working around it for the time being.
            for group in self.memberOf():
                if group in section.members:
                    results.append({'section': section,
                                    'group': group})

        return results
