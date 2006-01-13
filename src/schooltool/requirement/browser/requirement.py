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
schooltooo.requirement browser views.

$Id$
"""

from zope.app import zapi
from zope.app.form.browser.add import AddView
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from schooltool import SchoolToolMessage as _
import schooltool.app.browser.app
import schooltool.requirement.interfaces
from schooltool.batching import Batch


class RequirementAddView(AddView):
    """A view for adding Requirements."""

    def nextURL(self):
        return zapi.absoluteURL(self.context.context, self.request)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            return AddView.update(self)


class RequirementView(schooltool.app.browser.app.ContainerView):
    """A Requirement view."""

    __used_for__ = schooltool.requirement.interfaces.IRequirement

    index_title = _("Requirement index")
    add_title = _("Add a new Requirement")
    add_url = "+/addRequirement.html"

    def __init__(self, context, request, depth=None):
        schooltool.app.browser.app.ContainerView.__init__(self, context,
                                                          request)
        self.depth = depth
        if self.depth is None:
            self.depth = int(request.get('DEPTH', 3))

    def _search(self, searchstr, context):
        results = []
        for item in context.values():
            if searchstr.lower() in item.title.lower():
                results.append(item)
            results += self._search(searchstr, item)
        return results

    def update(self):
        if 'SEARCH' in self.request and 'CLEAR_SEARCH' not in self.request:
            searchstr = self.request['SEARCH'].lower()
            if self.request.get('RECURSIVE'):
                results = self._search(searchstr, self.context)
            else:
                results = [item for item in self.context.values()
                           if searchstr in item.title.lower()]
        else:
            self.request.form['SEARCH'] = ''
            results = self.context.values()

        start = int(self.request.get('batch_start', 0))
        size = int(self.request.get('batch_size', 10))
        self.batch = Batch(results, start, size, sort_by='title')

    def listContentInfo(self):
        children = []
        if self.depth < 1:
            return []
        for child in self.batch:
            if schooltool.requirement.interfaces.IRequirement.providedBy(child):
                info = {}
                info['child'] = child
                thread = RequirementView(child, self.request, self.depth-1)
                info['thread'] = thread.subthread()
                children.append(info)
        return children

    subthread = ViewPageTemplateFile('subthread.pt')


class RequirementEditView(schooltool.app.browser.app.BaseEditView):
    """View for editing Requirements."""

    __used_for__ = schooltool.requirement.interfaces.IRequirement

