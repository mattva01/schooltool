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

import datetime
from zope.interface import moduleProvides
from schooltool.interfaces import IApplication, IApplicationObjectContainer
from schooltool.interfaces import IModuleSetup, IResource
from schooltool.component import getPath, traverse
from schooltool.component import registerView
from schooltool.views import View, Template
from schooltool.views import TraversableView, XMLPseudoParser
from schooltool.views import absoluteURL, notFoundPage, textErrorPage
from schooltool.views.timetable import SchoolTimetableTraverseView
from schooltool.views.cal import AllCalendarsView, parse_date

__metaclass__ = type


moduleProvides(IModuleSetup)


class ApplicationView(TraversableView):
    """The root view for the application"""

    template = Template("www/app.pt", content_type="text/xml")

    def _traverse(self, name, request):
        if name == 'schooltt':
            return SchoolTimetableTraverseView(self.context)
        elif name == 'calendars.html':
            return AllCalendarsView(self.context)
        elif name == 'busysearch':
            return AvailabilityQueryView(self.context)
        else:
            return TraversableView._traverse(self, name, request)

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

    def __init__(self, container, name):
        View.__init__(self, container)
        self.name = name

    do_GET = staticmethod(notFoundPage)
    do_DELETE = staticmethod(notFoundPage)

    def do_PUT(self, request):
        return self.create(request, self.context, self.name)


class AvailabilityQueryView(View):

    template = Template("www/availability.pt", content_type="text/xml")

    def do_GET(self, request):
        """Parse the query and call the template rengering.

        Required arguments in the request query string:

            ======== ============  ===========
            Name     Type          Cardinality
            ======== ============  ===========
            first    'YYYY-MM-DD'  1
            last     'YYYY-MM-DD'  1
            duration int           1
            ======== ============  ===========

        Optional arguments (if not passed, 'all' assumed):

            ========= ==========  ===========
            Name      Type        Cardinality
            ========= ==========  ===========
            hours     int (0..23) many
            resources str         many
            ========= ==========  ===========

        """
        for arg in 'first', 'last', 'duration':
            if arg not in request.args:
                return textErrorPage(request,
                                     "%r argument must be provided" % arg)
        try:
            arg = 'first'
            self.first = parse_date(request.args['first'][0])
            arg = 'last'
            self.last = parse_date(request.args['last'][0])
            arg = 'duration'
            minutes = int(request.args['duration'][0])
            self.duration = datetime.timedelta(minutes=minutes)
            arg = 'hours'
            if 'hours' not in request.args:
                request.args['hours'] = range(24)
            self.hours = self.parseHours(request.args['hours'])
        except ValueError:
            return textErrorPage(request,
                                 "%r argument is invalid" % arg)
        self.resources = []
        if 'resources' not in request.args:
            resource_container = traverse(self.context, 'resources')
            request.args['resources'] = [getPath(obj) for obj in
                                         resource_container.itervalues()]
        for path in request.args['resources']:
            try:
                resource = traverse(self.context, path)
            except KeyError:
                return textErrorPage(request, "Invalid resource: %r" % path)
            if not IResource.isImplementedBy(resource):
                return textErrorPage(request, "%r is not a resource" % path)
            self.resources.append(resource)
        return View.do_GET(self, request)

    def parseHours(self, hours):
        hrs = map(int, hours)
        start = None
        results = []
        for hour in range(24):
            if hour in hrs:
                if start is None:
                    start = hour
            else:
                if start is not None:
                    results.append((datetime.time(start, 0),
                                    datetime.timedelta(hours=hour-start)))
                    start = None
        if start is not None:
            results.append((datetime.time(start, 0),
                            datetime.timedelta(hours=24-start)))
        return results

    def listResources(self):
        """The logic for the template"""
        results = []
        for resource in self.resources:
            slots = resource.getFreeIntervals(self.first, self.last,
                                              self.hours, self.duration)
            if slots:
                res_dict = {'path': getPath(resource), 'slots': []}
                results.append(res_dict)
                for start, duration in slots:
                    mins = duration.days * 60 * 24 + duration.seconds / 60
                    res_dict['slots'].append(
                        {'start': start.strftime("%Y-%m-%d %H:%M:%S"),
                         'duration': mins})
        return results


def setUp():
    """See IModuleSetup."""
    registerView(IApplication, ApplicationView)
    registerView(IApplicationObjectContainer, ApplicationObjectContainerView)

