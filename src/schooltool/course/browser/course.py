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

$Id$
"""
from zope.app import zapi
from zope.app.form.browser.add import AddView
from zope.publisher.browser import BrowserView
from zope.security.proxy import removeSecurityProxy

from schooltool.skin.containers import ContainerView
from schooltool.course.interfaces import ICourse, ICourseContainer, ISection
from schooltool.app.relationships import URIInstruction, URISection
from schooltool.app.membership import URIGroup, URIMembership
from schooltool.relationship import getRelatedObjects

from schooltool import SchoolToolMessage as _


class CourseContainerView(ContainerView):
    """A Course Container view."""

    __used_for__ = ICourseContainer

    index_title = _("Course index")


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
        return len(self.instructorOf()) > 0

    def isLearner(self):
        """Find out if the person is a member of any sections."""
        return len(self.learnerOf()) > 0

    def instructorOf(self):
        """Get the sections the person instructs."""
        sections = getRelatedObjects(self.context, URISection,
                                     rel_type=URIInstruction)
        results = []
        for section in sections:
            results.append({'title': removeSecurityProxy(section).title,
                            'section': section})
        return results

    def memberOf(self):
        """Seperate out generic groups from sections."""
        return [group for group in self.context.groups
                if not ISection.providedBy(group)]

    def learnerOf(self):
        """Get the sections the person is a member of."""
        results = []

        for item in self.context.groups:
            if ISection.providedBy(item):
                results.append({'section': item, 'group': None})
            else:
                group_sections = getRelatedObjects(item, URIGroup,
                                                   rel_type=URIMembership)
                for section in group_sections:
                    results.append({'section': section, 'group': item})

        return results
