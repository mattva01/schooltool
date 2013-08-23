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
"""
Views for the sample data generation
"""
from zope.publisher.browser import BrowserView
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import queryMultiAdapter, getUtilitiesFor
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.sampledata.generator import generate

from interfaces import ISampleDataPlugin

class SampleDataView(BrowserView):

    seed = 'SchoolTool'
    __used_for__ = ISchoolToolApplication

    template = ViewPageTemplateFile("sampledata.pt")

    work_done = property(lambda self: hasattr(self, 'times'))

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
                absoluteURL(self.context, self.request))
        if 'SUBMIT' in self.request:
            # TODO: maybe clear database here
            self.times = generate(self.context, self.seed,
                                  pluginNames=self._getSelectedPlugins())

    def _getSelectedPlugins(self):
        prefix = 'plugin.'
        for key in self.request.keys():
            if key.startswith(prefix):
                yield key[len(prefix):]

    def getPlugins(self):
        selectedPlugins = self._getSelectedPlugins()
        times = generate(self.context, self.seed,
                         dry_run=True, pluginNames=selectedPlugins)
        plugins = [obj for name, obj in getUtilitiesFor(ISampleDataPlugin)]
        result = []
        if 'CLEAR' in self.request:
            return plugins
        for plugin in plugins:
            data = {'name':plugin.name}
            if plugin.name in times.keys():
                data['selected'] = True
                view = queryMultiAdapter((plugin, self.request),
                                         name="options")
                data['view'] = view
            result.append(data)
        return result
