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
csv importing.

$Id$
"""
from zope.security.proxy import removeSecurityProxy
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.browser.csvimport import BaseCSVImporter, BaseCSVImportView
from schooltool.course.course import Course

from schooltool.common import SchoolToolMessage as _


class CourseCSVImporter(BaseCSVImporter):
    """Course CSV Importer"""

    factory = Course

    def createAndAdd(self, data, dry_run=True):
        """Create objects and add them to the container."""

        course_id = None
        government_id = None
        credits = None

        if len(data) < 1:
            self.errors.fields.append(_('Insufficient data provided.'))
            return

        if not data[0]:
            self.errors.fields.append(_('Titles may not be empty'))
            return

        if len(data) > 1:
            description = data[1]
        else:
            description = ''

        if len(data) > 2:
            if data[2]:
                course_id = data[2]
        else:
            for key, course in self.container.items():
                if course.title == data[0]:
                    course_id = key
                    break

        if course_id in self.container:
            obj = self.container[course_id]
            name = course_id
        else:
            obj = None

        if len(data) > 3:
            if data[3]:
                government_id = data[3]

        if len(data) > 4:
            try:
                credits = int(data[4])
            except (ValueError,):
                self.errors.fields.append(_('Course "${course_title}" credits "${invalid_credits}" value'
                                            ' must be an integer.',
                                            mapping={'course_title': data[0],
                                                     'invalid_credits': data[4]}))
                return

        if not obj:
            obj = self.factory(title=data[0], description=description)
            obj.course_id = course_id
            obj.government_id = government_id
            obj.credits = credits
            try:
                name = self.chooser.chooseName(course_id, obj)
            except ValueError, e:
                msg = e.args[0]
                self.errors.fields.append(_('Course "${course_title}" id "${invalid_id}"'
                                            ' is invalid. ${error_message}',
                                            mapping={'course_title': obj.title,
                                                     'invalid_id': course_id,
                                                     'error_message': msg}))
                return

        if not dry_run:
            if course_id in self.container:
                obj.title = data[0]
                obj.description = description
                obj.course_id = course_id
                obj.government_id = government_id
                obj.credits = credits
            else:
                self.container[name] = obj


class CourseCSVImportView(BaseCSVImportView):
    """View for Course CSV importer."""

    importer_class = CourseCSVImporter


class SectionMemberCSVImporter(BaseCSVImporter):
    """Section Member CSV Importer"""

    def createAndAdd(self, data, dry_run=True):
        """Create persons and add them to the section learners."""

        if len(data) < 1:
            self.errors.fields.append(_('Insufficient data provided.'))
            return

        if not data[0]:
            self.errors.fields.append(_('User names must not be empty.'))
            return

        app = ISchoolToolApplication(None)
        person_container = app['persons']
        username = data[0]

        if username not in person_container:
            self.errors.fields.append(_('"${username}" is not a valid username.',
                                        mapping={'username': username}))
            return

        user = person_container[username]
        if not dry_run:
            removeSecurityProxy(self.container.members).add(removeSecurityProxy(user))


class SectionMemberCSVImportView(BaseCSVImportView):
    """View for Section Member CSV importer."""

    importer_class = SectionMemberCSVImporter
