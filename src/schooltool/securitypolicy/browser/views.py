#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
"""
Configuration views for SchoolTool security policy.
"""

from zope.publisher.browser import BrowserView
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.securitypolicy.interfaces import IAccessControlCustomisations

from schooltool.common import SchoolToolMessage as _


class AccessControlView(BrowserView):

    def settings(self):
        """Returns a list of access control customisation settings."""
        app = ISchoolToolApplication(None)
        customisations = IAccessControlCustomisations(app)
        return list(customisations)

    def update(self):
        prefix = 'setting.'
        if 'UPDATE_SUBMIT' in self.request:
            for setting in self.settings():
                val = self.request.get(prefix + setting.key, 'False')
                setting.setValue(bool(val != 'False'))
        elif 'CANCEL' in self.request:
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)


class FlourishAccessControlView(AccessControlView):

    fieldset_titles = {
        'everyone_can_view_section_info': _('Section information'),
        'instructors_can_edit_section': _('Section information'),
        'everyone_can_view_person_list': _('List of accounts'),
        'persons_can_set_their_preferences': _('User calendars'),
        'persons_can_change_their_passwords': _('User passwords'),
        'everyone_can_view_group_list': _('List of groups'),
        'everyone_can_view_group_info': _('Group information'),
        'everyone_can_view_group_calendar': _('View group calendars'),
        'members_can_edit_group_calendar': _('Edit group calendars'),
        'everyone_can_view_resource_list': _('List of resources'),
        'everyone_can_view_resource_info': _('Resource information'),
        'everyone_can_view_resource_calendar': _('Resource calendars'),
        'instructors_can_schedule_sections': _('Schedules'),
        'administration_can_grade_students': _('Gradebook'),
        'administration_can_grade_journal': _('Journal'),
        }

    def fieldsets(self):
        for setting in self.settings():
            info = {'legend': self.fieldset_titles[setting.key],
                    'setting': setting}
            yield info

    def update(self):
        prefix = 'setting.'
        self.status = None
        if 'UPDATE_SUBMIT' in self.request:
            for setting in self.settings():
                val = self.request.get(prefix + setting.key, 'False')
                setting.setValue(bool(val != 'False'))
            url = absoluteURL(self.context, self.request) + '/security.html'
            self.request.response.redirect(url)
        elif 'CANCEL' in self.request:
            url = absoluteURL(self.context, self.request) + '/security.html'
            self.request.response.redirect(url)
