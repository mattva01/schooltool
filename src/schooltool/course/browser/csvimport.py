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
"""Course CSV import
"""
from decimal import Decimal, InvalidOperation

from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser.absoluteurl import absoluteURL

import schooltool.skin.flourish.page
from schooltool.app.browser.app import ActiveSchoolYearContentMixin
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.browser.csvimport import BaseCSVImporter
from schooltool.app.browser.csvimport import BaseCSVImportView
from schooltool.app.browser.csvimport import FlourishBaseCSVImportView
from schooltool.course.course import Course
from schooltool.course.interfaces import ICourseContainer
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin import flourish

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
                credits = Decimal(data[4])
            except (ValueError, InvalidOperation):
                self.errors.fields.append(_('Course "${course_title}" credits "${invalid_credits}" value'
                                            ' must be a number.',
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


class FlourishCourseCSVImportView(FlourishBaseCSVImportView, ActiveSchoolYearContentMixin):

    importer_class = CourseCSVImporter

    @property
    def schoolyear(self):
        return ISchoolYear(self.context)

    def nextURL(self):
        app = ISchoolToolApplication(None)
        return self.url_with_schoolyear_id(app, view_name='courses')


class ImportCoursesLinkViewlet(flourish.page.LinkViewlet,
                               ActiveSchoolYearContentMixin):

    @property
    def enabled(self):
        courses = ICourseContainer(self.schoolyear)
        if not flourish.canEdit(courses):
            return False
        return super(ImportCoursesLinkViewlet, self).enabled

    @property
    def url(self):
        link = self.link
        if not link:
            return None
        courses = ICourseContainer(self.schoolyear)
        return "%s/%s" % (absoluteURL(courses, self.request),
                          self.link)


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


class FlourishSectionMemberCSVImportView(FlourishBaseCSVImportView):

    importer_class = SectionMemberCSVImporter

    def nextURL(self):
        return absoluteURL(self.context, self.request)
