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
Views for the sample data generation

$Id$
"""
from zope.app import zapi
from zope.app.publisher.browser import BrowserView
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.sampledata.generator import generate


class SampleDataView(BrowserView):

    seed = 'SchoolTool'
    __used_for__ = ISchoolToolApplication

    template = ViewPageTemplateFile("sampledata.pt")

    def __call__(self):
        self.update()
        return self.template()

    def update(self):
        if 'seed' in self.request:
            self.seed = self.request['seed']
            if self.seed == '':
                self.seed = None
        if 'CANCEL' in self.request:
            self.request.response.redirect(
                zapi.absoluteURL(self.context, self.request))
        if 'SUBMIT' in self.request:
            # TODO: maybe clear database here
            self.times = generate(self.context, self.seed)
