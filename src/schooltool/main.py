#!/usr/bin/env python2.3
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
Schooltool HTTP server.
"""

import os
import sys
import ZConfig
from twisted.web import server, resource
from twisted.internet import reactor
from zope.pagetemplate.pagetemplatefile import PageTemplateFile

__metaclass__ = type


#
# Some fake content
#

class FakePerson:

    def __init__(self, name):
        self.name = name

class FakeApplication:

    people = {'john': FakePerson('john'),
              'smith': FakePerson('smith'),
              'george': FakePerson('george')}


#
# Page templates
#

class Template(PageTemplateFile):
    """Page template file.

    Character set for rendered pages can be set by changing the 'charset'
    attribute.  You should not change the default (UTF-8) without a good
    reason.  If the page template contains characters not representable
    in the output charset, a UnicodeError will be raised when rendering.
    """

    charset = 'UTF-8'

    def __call__(self, request, **kw):
        """Renders the page template.

        Any keyword arguments passed to this function will be accessible
        in the page template namespace.
        """
        request.setHeader('Content-Type',
                          'text/html; charset=%s' % self.charset)
        context = self.pt_getContext()
        context['request'] = request
        context.update(kw)
        return self.pt_render(context).encode(self.charset)


#
# HTTP view infrastructure
#

class ErrorView(resource.Resource):
    """View for an error.

    Rendering this view will set the appropriate HTTP status code and reason.
    """

    __super = resource.Resource
    __super___init__ = __super.__init__

    isLeaf = True

    template = Template('www/error.pt')

    def __init__(self, code, reason):
        self.__super___init__()
        self.code = code
        self.reason = reason

    def render(self, request):
        request.setResponseCode(self.code, self.reason)
        return self.template(request, code=self.code, reason=self.reason)


class NotFoundView(ErrorView):
    """View for a not found error.

    This view should be used for HTTP status code 404.
    """

    template = Template('www/notfound.pt')


def errorPage(request, code, reason):
    """Renders a simple error page and sets the HTTP status code and reason."""
    return ErrorView(code, reason).render(request)


class View(resource.Resource):
    """View for a content component.

    A View is a kind of a Resource in twisted.web sense, but it is really just
    a view for the actual resource, which is a content component.

    Subclasses could provide the following methods and attributes:

        template    attribute that contains a Template instance for rendering
        _traverse   method that should return a view for a contained object
                    or raise a KeyError

    """

    __super = resource.Resource
    __super___init__ = __super.__init__
    __super_getChild = __super.getChild

    def __init__(self, context):
        self.__super___init__()
        self.context = context

    def getChild(self, name, request):
        if name == '': # trailing slash in the URL?
            return self
        try:
            return self._traverse(name, request)
        except KeyError:
            return NotFoundView(404, "Not found")
        return self.__super_getChild(name, request)

    def _traverse(self, name, request):
        raise KeyError(name)

    def render(self, request):
        if request.method == 'GET':
            return self.template(request, view=self, context=self.context)
        else:
            return errorPage(request, 405, "Method not allowed")


#
# Actual views
#

class RootView(View):
    """View for the application root."""

    template = Template('www/root.pt')

    def _traverse(self, name, request):
        if name == 'people':
            return PeopleView(self.context)
        raise KeyError(name)


class PeopleView(View):
    """View for /people"""

    template = Template('www/people.pt')

    def listNames(self):
        """Lists the names of all persons known to the system.

        Names are sorted in alphabetical order.
        """
        people = self.context.people.items()
        people.sort()
        return [k for k, v in people]

    def _traverse(self, name, request):
        person = self.context.people[name]
        return PersonView(person)


class PersonView(View):
    """View for /people/person_name"""

    template = Template('www/person.pt')


#
# Main loop
#

def main():
    """Starts the SchoolTool mockup HTTP server on port 8080."""
    dirname = os.path.dirname(__file__)
    schema = ZConfig.loadSchema(os.path.join(dirname, 'schema.xml'))
    filename = os.path.join(dirname, '..', '..', 'schooltool.conf')
    if not os.path.exists(filename):
        filename = os.path.join(dirname, '..', '..', 'schooltool.conf.in')
    config, handler = ZConfig.loadConfig(schema, filename)

    site = server.Site(RootView(FakeApplication()))
    for interface, port in config.listen:
        reactor.listenTCP(port, site, interface=interface)
        print "Started HTTP server on %s:%s" % (interface or "*", port)
    reactor.run()


if __name__ == '__main__':
    main()

