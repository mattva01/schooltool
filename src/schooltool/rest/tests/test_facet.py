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
Unit tests for schooltool.rest.facet

$Id$
"""

import sets
from logging import INFO
import unittest
from zope.interface import implements
from persistent import Persistent
from schooltool.interfaces import IFacet, IFaceted
from schooltool.tests.helpers import diff
from schooltool.tests.utils import RegistriesSetupMixin
from schooltool.tests.utils import XMLCompareMixin
from schooltool.tests.utils import QuietLibxml2Mixin
from schooltool.rest.tests import RequestStub, setPath

__metaclass__ = type


class IFacetStub(IFacet):
    pass


class FacetStub(Persistent):

    implements(IFacetStub)

    def __init__(self, name=None, active=True, parent=None, owner=None):
        self.__name__ = name
        self.__parent__ = parent
        self.active = active
        self.owner = owner


class FacetedStub:

    implements(IFaceted)

    def __init__(self, initial=()):
        from schooltool.db import PersistentKeysSetContainer
        self.__facets__ = PersistentKeysSetContainer('facets', self, IFacet)
        for facet in initial:
            self.__facets__.add(facet, name=None)


class FacetManagerStub:

    def __init__(self):
        self.facets = {}

    def facetByName(self, name):
        return self.facets[name]


class TestFacetView(XMLCompareMixin, RegistriesSetupMixin, unittest.TestCase):

    def setUp(self):
        self.setUpRegistries()
        from schooltool import rest
        rest.setUp()

    def tearDown(self):
        self.tearDownRegistries()

    def createView(self, facet_name="001"):
        from schooltool.rest.facet import FacetView
        self.facet = FacetStub(name=facet_name)
        view = FacetView(self.facet)
        view.authorization = lambda ctx, rq: True
        return view

    def test_render(self):
        view = self.createView()
        request = RequestStub("http://localhost/some/object/facets/001")
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <facet active="active" owned="unowned">
              <class>FacetStub</class>
              <name>001</name>
            </facet>
            """)

        self.facet.active = False
        self.facet.owner = object()
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <facet active="inactive" owned="owned">
              <class>FacetStub</class>
              <name>001</name>
            </facet>
            """)

    def test_delete_owned(self):
        view = self.createView()
        request = RequestStub("http://localhost/some/object/facets/001",
                              method="DELETE")
        self.facet.owner = object()
        result = view.render(request)
        self.assertEquals(request.code, 400)
        self.assertEquals(request.reason, "Bad Request")
        self.assertEquals(request.applog, [])
        self.assertEquals(result, "Owned facets may not be deleted manually")

    def test_delete_unowned(self):
        view = self.createView(facet_name=None)
        facetedstub = FacetedStub([self.facet])
        setPath(facetedstub, '/person')
        request = RequestStub("http://localhost/some/object/facets/001",
                              method="DELETE")
        result = view.render(request)
        expected = "Facet /person/facets/001 (FacetStub) removed"
        self.assertEquals(result, expected, "\n" + diff(expected, result))
        self.assertEquals(request.applog,
                  [(None, expected, INFO)])


class TestFacetManagementView(XMLCompareMixin, RegistriesSetupMixin,
                              QuietLibxml2Mixin, unittest.TestCase):

    def setUp(self):
        self.setUpRegistries()
        self.setUpLibxml2()

    def tearDown(self):
        self.tearDownRegistries()
        self.tearDownLibxml2()

    def test_traverse(self):
        from schooltool.rest import View
        from schooltool.rest.facet import FacetManagementView
        from schooltool.component import registerView
        registerView(IFacetStub, View)

        context = FacetManagerStub()
        facet = FacetStub()
        context.facets['foo'] = facet
        view = FacetManagementView(context)
        request = RequestStub()
        self.assertRaises(KeyError, view._traverse, 'bar', request)
        child = view._traverse('foo', request)
        self.assertEquals(child.context, facet)

    def test_get(self):
        from schooltool.rest.facet import FacetManagementView
        from schooltool.component import FacetManager
        from schooltool.model import Person
        from schooltool.eventlog import EventLogFacet
        import schooltool.eventlog
        schooltool.eventlog.setUp() # register a facet factory

        request = RequestStub("http://localhost/person/facets")
        facetable = Person()
        owner = Person()
        setPath(facetable, '/person')
        context = FacetManager(facetable)
        facet = EventLogFacet()
        context.setFacet(facet)
        facet.active = False
        context.setFacet(EventLogFacet(), owner=owner)
        view = FacetManagementView(context)
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.headers['content-type'],
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <facets xmlns:xlink="http://www.w3.org/1999/xlink">
              <facet active="active" owned="owned"
                     xlink:href="/person/facets/person_info"
                     xlink:title="person_info"
                     xlink:type="simple"/>
              <facet xlink:type="simple" active="inactive"
                     xlink:title="001"
                     owned="unowned" xlink:href="/person/facets/001"/>
              <facet xlink:type="simple" active="active"
                     xlink:title="002"
                     owned="owned" xlink:href="/person/facets/002"/>
              <facetFactory name="eventlog" title="Event Log"/>
            </facets>
            """, recursively_sort=["facets"])

    def test_post(self):
        from schooltool.rest.facet import FacetManagementView
        from schooltool.component import FacetManager
        from schooltool.model import Person
        from schooltool.eventlog import EventLogFacet
        import schooltool.eventlog
        schooltool.eventlog.setUp()

        xml = '''<facet xmlns="http://schooltool.org/ns/model/0.1"
                        factory="eventlog"/>'''
        request = RequestStub("http://localhost/p1/facets",
                              method="POST", body=xml)
        facetable = Person()
        setPath(facetable, '/p1')
        context = FacetManager(facetable)
        view = FacetManagementView(context)
        self.assertEquals(len(list(context.iterFacets())), 1)
        view.authorization = lambda ctx, rq: True
        result = view.render(request)
        self.assertEquals(request.applog,
              [(None, "Facet /p1/facets/eventlog (EventLogFacet) created",
                INFO)])
        self.assertEquals(request.code, 201)
        self.assertEquals(request.reason, "Created")
        baseurl = "http://localhost:7001/p1/facets/"
        location = request.headers['location']
        self.assert_(location.startswith(baseurl),
                     "%r.startswith(%r) failed" % (location, baseurl))
        name = location[len(baseurl):]
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")
        self.assert_(location in result)
        self.assertEquals(len(list(context.iterFacets())), 2)
        facet = context.facetByName(name)
        self.assert_(facet.__class__ is EventLogFacet)
        self.assertEquals(name, 'eventlog')

    def test_post_errors(self):
        from schooltool.rest.facet import FacetManagementView
        from schooltool.component import FacetManager
        from schooltool.model import Person
        import schooltool.eventlog
        schooltool.eventlog.setUp()
        facetable = Person()
        context = FacetManager(facetable)
        view = FacetManagementView(context)
        view.authorization = lambda ctx, rq: True
        for body in ("foo", '<facet factory="eventlog">',
                     '<facet xmlns="http://schooltool.org/ns/model/0.1"'
                     ' factory="nosuchfactory"/>',
                     '<facet xmlns="http://schooltool.org/ns/model/0.1"'
                     ' factory="nosuchfactory \xe2\x98\xbb"/>'):
            request = RequestStub("http://localhost/group/facets",
                                  method="POST",
                                  body=body)
            result = view.render(request)
            self.assertEquals(request.applog, [])
            self.assertEquals(request.code, 400,
                              "%s != 400 for %s" % (request.code, body))
            self.assertEquals(request.headers['content-type'],
                              "text/plain; charset=UTF-8")

    def test_post_singleton_twice(self):
        from schooltool.rest.facet import FacetManagementView
        from schooltool.component import FacetManager
        from schooltool.model import Person
        from schooltool.eventlog import EventLogFacet
        import schooltool.eventlog
        schooltool.eventlog.setUp() # register a facet factory
        facetable = Person()
        context = FacetManager(facetable)
        view = FacetManagementView(context)
        view.authorization = lambda ctx, rq: True
        context.setFacet(EventLogFacet(), name='eventlog')
        request = RequestStub("http://localhost/group/facets",
                              method="POST",
                              body='facet factory="eventlog"')
        result = view.render(request)
        self.assertEquals(request.applog, [])
        self.assertEquals(request.code, 400)
        self.assertEquals(request.headers['content-type'],
                          "text/plain; charset=UTF-8")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestFacetView))
    suite.addTest(unittest.makeSuite(TestFacetManagementView))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
