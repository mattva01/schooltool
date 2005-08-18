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
from zope.app import zapi
from zope.app.publisher.browser import BrowserView

from schoolbell.relationship import getRelatedObjects
from schoolbell.app.interfaces import ISchoolBellCalendar
from schoolbell.app.person.browser import person

from schooltool import getSchoolToolApplication
from schooltool.course.interfaces import ISection
from schooltool.interfaces import IApplicationPreferences
from schooltool.interfaces import ISchoolToolApplication
from schooltool.relationships import URIInstruction, URISection


class SchoolToolApplicationView(BrowserView):
    """A view for the main application."""

    def update(self):
        prefs = IApplicationPreferences(getSchoolToolApplication())
        if prefs.frontPageCalendar:
            url = zapi.absoluteURL(ISchoolBellCalendar(self.context),
                                   self.request)
            self.request.response.redirect(url)


class PersonView(person.PersonView):
    """Add additional information to the Person view.

    Tal friendly methods for determining if a person is a teacher or a
    student.
    """

    def isTeacher(self):

        if len(getRelatedObjects(self.context, URISection,
                                 rel_type=URIInstruction)) > 0:
            return True
        else:
            return False

    def isLearner(self):
        for obj in self.context.groups:
            if ISection.providedBy(obj):
                return True

        return False

    def instructorOf(self):
        return getRelatedObjects(self.context, URISection,
                                 rel_type=URIInstruction)

    def memberOf(self):
        """Seperate out generic groups from sections."""

        return [group for group in self.context.groups if not
                ISection.providedBy(group)]

    def learnerOf(self):
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
