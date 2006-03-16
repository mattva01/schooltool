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
Views for the setup data generation

$Id: browser.py 5225 2005-10-12 18:02:40Z alga $
"""
from zope.app import zapi
from zope.app.publisher.browser import BrowserView
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.setupdata.generator import generate


class SetupDataView(BrowserView):

    __used_for__ = ISchoolToolApplication

    template = ViewPageTemplateFile("setupdata.pt")

    work_done = property(lambda self: hasattr(self, 'times'))

    def __call__(self):
        self.update()
        return self.template()

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(
                zapi.absoluteURL(self.context, self.request))
        if 'SUBMIT' in self.request:
            # TODO: maybe clear database here
            self.times = generate(self.context)
