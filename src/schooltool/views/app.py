#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
The views for the schooltool.app objects.

$Id$
"""

from zope.interface import moduleProvides
from schooltool.interfaces import IApplication, IApplicationObjectContainer
from schooltool.interfaces import IModuleSetup
from schooltool.component import getPath
from schooltool.component import registerView
from schooltool.views import View, Template
from schooltool.views import TraversableView, XMLPseudoParser
from schooltool.views import absoluteURL

__metaclass__ = type


moduleProvides(IModuleSetup)


class ApplicationView(TraversableView):
    """The root view for the application"""

    template = Template("www/app.pt", content_type="text/xml")

    def getRoots(self):
        return [{'path': getPath(root), 'title': root.title}
                for root in self.context.getRoots()]

    def getContainers(self):
        base = getPath(self.context)
        if not base.endswith('/'):
            base += '/'
        return [{'path': '%s%s' % (base, key), 'title': key}
                for key in self.context.keys()]

    def getUtilities(self):
        return [{'path': getPath(utility), 'title': utility.title}
                for utility in self.context.utilityService.values()]


class ApplicationObjectCreator(XMLPseudoParser):
    """Mixin for adding new application objects"""

    def create(self, request, container, name=None):
        body = request.content.read()
        kw = {}
        if name is not None:
            kw['__name__'] = name
        try:
            kw['title'] = self.extractKeyword(body, 'title')
        except KeyError:
            pass
        obj = container.new(**kw)
        location = absoluteURL(request, getPath(obj))
        request.setResponseCode(201, 'Created')
        request.setHeader('Content-Type', 'text/plain')
        request.setHeader('Location', location)
        return "Object created: %s" % location


class ApplicationObjectContainerView(TraversableView,
                                     ApplicationObjectCreator):
    """The view for the application object containers"""

    template = Template("www/aoc.pt", content_type="text/xml")

    def getName(self):
        return self.context.__name__

    def items(self):
        c = self.context
        return [{'path': getPath(c[key]), 'title': c[key].title}
                for key in self.context.keys()]

    def _traverse(self, name, request):
        try:
            return TraversableView._traverse(self, name, request)
        except KeyError:
            return ApplicationObjectCreatorView(self.context, name)

    def do_POST(self, request):
        return self.create(request, self.context)


class ApplicationObjectCreatorView(View, ApplicationObjectCreator):
    """View for non-existing application objects"""

    template = Template('www/notfound.pt')
    code = 404
    reason = "Not Found"

    def __init__(self, container, name):
        View.__init__(self, None)
        self.container = container
        self.name = name

    def do_GET(self, request):
        request.setResponseCode(self.code, self.reason)
        return self.template(request, code=self.code, reason=self.reason)

    do_DELETE = do_GET

    def do_PUT(self, request):
        return self.create(request, self.container, self.name)


def setUp():
    """See IModuleSetup."""
    registerView(IApplication, ApplicationView)
    registerView(IApplicationObjectContainer, ApplicationObjectContainerView)

