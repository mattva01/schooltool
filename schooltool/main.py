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

from twisted.web import server, resource
from twisted.internet import reactor

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
# HTTP views
#

class View(resource.Resource):
    """View for a content component.

    A View is a kind of a Resource in twisted.web sense, but it is really just
    a view for the actual resource, which is a content component.

    Subclasses should override getChild for traversal and render for rendering.
    """

    __super = resource.Resource
    __super___init__ = __super.__init__

    def __init__(self, context):
        self.__super___init__()
        self.context = context


class RootView(View):

    __super_getChild = View.getChild

    def getChild(self, name, request):
        if name == '':
            return self
        if name == 'people':
            return PeopleView(self.context)
        return self.__super_getChild(name, request)

    def render(self, request):
        if request.method == 'GET':
            # XXX use a page template
            result = ["<html><head><title>SchoolTool prototype</title></head>"
                      "<body><h1>Prototype</h1>"
                      "<p>This is a very early prototype of a SchoolTool HTTP server.</p>"
                      "<p>See a <a href=\"people\">list of persons</a></p>"
                      "</body></html>"]
            return "".join(result)
        else:
            return errorPage(request, 405, "Method not allowed")


class PeopleView(View):

    __super_getChild = View.getChild

    def listNames(self):
        people = self.context.people.items()
        people.sort()
        return [k for k, v in people]

    def getChild(self, name, request):
        if name == '':
            return self
        if name in self.context.people:
            return PersonView(self.context.people[name])
        return self.__super_getChild(name, request)

    def render(self, request):
        if request.method == 'GET':
            # XXX use a page template
            result = ["<html><head><title>People</title></head>"
                      "<body><h1>People</h1><ul>"
                     ] + ["<li><a href=\"/people/%s\">%s</li>" % (person, person)
                          for person in self.listNames()
                     ] + ["</ul></body></html>"]
            return "".join(result)
        else:
            return errorPage(request, 405, "Method not allowed")


class PersonView(View):

    def render(self, request):
        if request.method == 'GET':
            # XXX use a page template
            name = self.context.name
            result = ["<html><head><title>%s</title></head>" % name,
                      "<body><h1>%s</h1>" % name,
                      "<p>This is an informative page about %s</p>" % name,
                      "</body></html>"]
            return "".join(result)
        else:
            return errorPage(request, 405, "Method not allowed")


def errorPage(request, code, message):
    """Convenience function for setting HTTP response code and formatting a
    simple error page."""
    # XXX use a page template
    request.setResponseCode(code, message)
    s = "%d - %s" % (code, message)
    return ("<html><head><title>%s</title></head>"
            "<body><h1>%s</h1></body></html>" % (s, s))


def main():
    # XXX: hook up zconfig
    site = server.Site(RootView(FakeApplication()))
    reactor.listenTCP(8080, site)
    reactor.run()

if __name__ == '__main__':
    main()

