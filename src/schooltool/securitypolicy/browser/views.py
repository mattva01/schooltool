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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Configuration views for SchoolTool security policy.

$Id$
"""

from zope.publisher.browser import BrowserView
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.securitypolicy.interfaces import IAccessControlCustomisations


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
                setting.setValue(prefix + setting.key in self.request)
        elif 'CANCEL' in self.request:
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)

