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
Tests for schollbell.rest.app

$Id$
"""

import unittest
import doctest
from StringIO import StringIO

from zope.app.testing import ztapi
from zope.testing import doctest
from zope.publisher.interfaces import NotFound
from zope.interface.verify import verifyObject
from zope.interface import directlyProvides, Interface
from zope.app.traversing.interfaces import ITraversable
from zope.publisher.browser import TestRequest
from zope.app.testing import setup
from zope.app.traversing.interfaces import IContainmentRoot
from zope.app.container.interfaces import INameChooser
import zope

from schoolbell.app.app import SimpleNameChooser, Group, Person, Resource
from schoolbell.app.rest.app import GroupContainerView, ResourceContainerView
from schoolbell.app.rest.app import PersonContainerView

from schoolbell.app.rest.app import GroupView, ResourceView, PersonView
from schoolbell.app.rest.app import GroupFile, PersonFile, ResourceFile

from schoolbell.app.interfaces import IGroupContainer, IResourceContainer
from schoolbell.app.interfaces import IPersonContainer


from schoolbell.app.rest.tests.utils import XMLCompareMixin, QuietLibxml2Mixin
from schoolbell.app.rest.xmlparsing import XMLDocument, XMLParseError


class TestAppView(XMLCompareMixin, unittest.TestCase):

    def setUp(self):
        from schoolbell.app.rest.app import ApplicationView
        from schoolbell.app.app import SchoolBellApplication
        setup.placefulSetUp()
        self.app = SchoolBellApplication()
        directlyProvides(self.app, IContainmentRoot)
        self.view = ApplicationView(self.app, TestRequest())

    def tearDown(self):
        setup.placefulTearDown()

    def test_render_Usingxpath(self):
        result = self.view.GET()

        doc = XMLDocument(result)
        doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')

        def oneNode(expr):
            nodes = doc.query(expr)
            self.assertEquals(len(nodes), 1,
                              "%s matched %d nodes" % (expr, len(nodes)))
            return nodes[0]

        try:
            nodes = doc.query('/schooltool/containers')
            self.assertEquals(len(nodes), 1)
            nodes = doc.query('/schooltool/containers/container')
            self.assertEquals(len(nodes), 3)

            persons = oneNode('/schooltool/containers/container'
                              '[@xlink:href="http://127.0.0.1/persons"]')
            self.assertEquals(persons['xlink:type'], 'simple')
            self.assertEquals(persons['xlink:title'], 'persons')

            groups = oneNode('/schooltool/containers/container'
                             '[@xlink:href="http://127.0.0.1/groups"]')
            self.assertEquals(groups['xlink:type'], 'simple')
            self.assertEquals(groups['xlink:title'], 'groups')

            notes = oneNode('/schooltool/containers/container'
                            '[@xlink:href="http://127.0.0.1/resources"]')
            self.assertEquals(notes['xlink:type'], 'simple')
            self.assertEquals(notes['xlink:title'], 'resources')
        finally:
            doc.free()

    def test_render(self):
        result = self.view.GET()
        response = self.view.request.response
        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <schooltool xmlns:xlink="http://www.w3.org/1999/xlink">
              <message>Welcome to the SchoolBell server</message>
              <containers>
                <container xlink:type="simple"
                           xlink:href="http://127.0.0.1/persons"
                           xlink:title="persons"/>
                <container xlink:href="http://127.0.0.1/resources"
                           xlink:title="resources"
                           xlink:type="simple"/>
                <container xlink:type="simple"
                           xlink:href="http://127.0.0.1/groups"
                           xlink:title="groups"/>
              </containers>
            </schooltool>
            """, recursively_sort=["schooltool"])


class ContainerViewTestMixin(XMLCompareMixin, QuietLibxml2Mixin):
    """Common code for Container View tests"""

    def setUp(self):
        from schoolbell.app.app import SchoolBellApplication
        from schoolbell.app.rest.app import GroupFileFactory
        from schoolbell.app.rest.app import ResourceFileFactory
        from zope.app.filerepresentation.interfaces import IFileFactory

        setup.placefulSetUp()
        self.setUpLibxml2()

        ztapi.provideView(Interface, Interface, ITraversable, 'view',
                          zope.app.traversing.namespace.view)
        ztapi.provideAdapter(IGroupContainer,
                             INameChooser,
                             SimpleNameChooser)
        ztapi.provideAdapter(IGroupContainer,
                             IFileFactory,
                             GroupFileFactory)
        ztapi.provideAdapter(IResourceContainer,
                             IFileFactory,
                             ResourceFileFactory)


        self.app = SchoolBellApplication()
        directlyProvides(self.app, IContainmentRoot)

    def tearDown(self):
        self.tearDownLibxml2()
        setup.placefulTearDown()


class TestGroupContainerView(ContainerViewTestMixin,
                             unittest.TestCase):
    """Test for GroupContainerView"""

    def setUp(self):
        ContainerViewTestMixin.setUp(self)
        from schoolbell.app.app import Group

        self.group = self.app['groups']['root'] = Group("Root group")
        self.groupContainer = self.app['groups']

    def test_render(self):
        view = GroupContainerView(self.groupContainer,
                                  TestRequest())
        result = view.GET()
        response = view.request.response

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>groups</name>
              <items>
                <item xlink:href="http://127.0.0.1/groups/root"
                      xlink:type="simple" xlink:title="Root group"/>
              </items>
              <acl xlink:href="http://127.0.0.1/groups/acl" xlink:title="ACL"
                   xlink:type="simple"/>
            </container>
            """)

    def test_post(self, suffix="", view=None,
                  body="""<object xmlns="http://schooltool.org/ns/model/0.1"
                                  title="New Group"/>"""):
        view = GroupContainerView(self.groupContainer,
                                  TestRequest(StringIO(body)))
        result = view.POST()
        response = view.request.response

        self.assertEquals(response.getStatus(), 201)
        self.assertEquals(response._reason, "Created")

        location = response.getHeader('location')
        base = "http://127.0.0.1/groups/"
        self.assert_(location.startswith(base),
                     "%r.startswith(%r) failed" % (location, base))
        name = location[len(base):]
        self.assert_(name in self.app['groups'].keys())
        self.assertEquals(response.getHeader('content-type'),
                          "text/plain; charset=UTF-8")
        self.assert_(location in result)
        return name

    def test_post_with_a_description(self):
        name = self.test_post(body='''
            <object title="New Group"
                    description="A new group"
                    xmlns='http://schooltool.org/ns/model/0.1'/>''')
        self.assertEquals(self.app['groups'][name].title, 'New Group')
        self.assertEquals(self.app['groups'][name].description, 'A new group')
        self.assertEquals(name, 'new-group')

    def test_post_error(self):
        view = GroupContainerView(
            self.groupContainer,
            TestRequest(StringIO('<element title="New Group">')))
        self.assertRaises(XMLParseError, view.POST)


class TestResourceContainerView(ContainerViewTestMixin,
                             unittest.TestCase):
    """Test for ResourceContainerView"""

    def setUp(self):
        ContainerViewTestMixin.setUp(self)
        from schoolbell.app.app import Resource

        self.resource = self.app['resources']['root'] = Resource("Root resource")
        self.resourceContainer = self.app['resources']

    def test_render(self):
        view = ResourceContainerView(self.resourceContainer,
                                  TestRequest())
        result = view.GET()
        response = view.request.response

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>resources</name>
              <items>
                <item xlink:href="http://127.0.0.1/resources/root"
                      xlink:type="simple" xlink:title="Root resource"/>
              </items>
              <acl xlink:href="http://127.0.0.1/resources/acl" xlink:title="ACL"
                   xlink:type="simple"/>
            </container>
            """)

    def test_post(self, suffix="", view=None,
                  body="""<object xmlns="http://schooltool.org/ns/model/0.1"
                                  title="New Resource"/>"""):
        view = ResourceContainerView(self.resourceContainer,
                                  TestRequest(StringIO(body)))
        result = view.POST()
        response = view.request.response

        self.assertEquals(response.getStatus(), 201)
        self.assertEquals(response._reason, "Created")

        location = response.getHeader('location')
        base = "http://127.0.0.1/resources/"
        self.assert_(location.startswith(base),
                     "%r.startswith(%r) failed" % (location, base))
        name = location[len(base):]
        self.assert_(name in self.app['resources'].keys())
        self.assertEquals(response.getHeader('content-type'),
                          "text/plain; charset=UTF-8")
        self.assert_(location in result)
        return name

    def test_post_with_a_description(self):
        name = self.test_post(body='''
            <object title="New Resource"
                    description="A new resource"
                    xmlns='http://schooltool.org/ns/model/0.1'/>''')
        self.assertEquals(self.app['resources'][name].title, 'New Resource')
        self.assertEquals(self.app['resources'][name].description, 'A new resource')
        self.assertEquals(name, 'Resource')

    def test_post_error(self):
        view = ResourceContainerView(
            self.resourceContainer,
            TestRequest(StringIO('<element title="New Resource">')))
        self.assertRaises(XMLParseError, view.POST)


class TestPersonContainerView(ContainerViewTestMixin,
                             unittest.TestCase):
    """Test for PersonContainerView"""

    def setUp(self):
        ContainerViewTestMixin.setUp(self)
        from schoolbell.app.app import Person

        self.person = self.app['persons']['root'] = Person("root",
                                                           "Root person")
        self.personContainer = self.app['persons']

    def test_render(self):
        view = PersonContainerView(self.personContainer,
                                  TestRequest())
        result = view.GET()
        response = view.request.response

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result, """
            <container xmlns:xlink="http://www.w3.org/1999/xlink">
              <name>persons</name>
              <items>
                <item xlink:href="http://127.0.0.1/persons/root"
                      xlink:type="simple" xlink:title="Root person"/>
              </items>
              <acl xlink:href="http://127.0.0.1/persons/acl" xlink:title="ACL"
                   xlink:type="simple"/>
            </container>
            """)


class TestGroupFileFactory(unittest.TestCase):

    def setUp(self):
        from schoolbell.app.app import GroupContainer
        from schoolbell.app.rest.app import GroupFileFactory

        self.groupContainer = GroupContainer()
        self.factory = GroupFileFactory(self.groupContainer)

    def test_title(self):
        group = self.factory("new_group", None,
                     '''<object xmlns="http://schooltool.org/ns/model/0.1"
                                title="New Group"/>''')

        self.assertEquals(group.title, "New Group")

    def test_description(self):
        group = self.factory("new_group", None,
                     '''<object xmlns="http://schooltool.org/ns/model/0.1"
                                title="New Group"
                                description="Boo"/>''')

        self.assertEquals(group.title, "New Group")
        self.assertEquals(group.description, "Boo")


class TestResourceFileFactory(unittest.TestCase):

    def setUp(self):
        from schoolbell.app.app import ResourceContainer
        from schoolbell.app.rest.app import ResourceFileFactory

        self.resourceContainer = ResourceContainer()
        self.factory = ResourceFileFactory(self.resourceContainer)

    def test_title(self):
        resource = self.factory("new_resource", None,
                     '''<object xmlns="http://schooltool.org/ns/model/0.1"
                                title="New Resource"/>''')

        self.assertEquals(resource.title, "New Resource")

    def test_description(self):
        resource = self.factory("new_resource", None,
                     '''<object xmlns="http://schooltool.org/ns/model/0.1"
                                title="New Resource"
                                description="Boo"/>''')

        self.assertEquals(resource.title, "New Resource")
        self.assertEquals(resource.description, "Boo")


class TestPersonFileFactory(unittest.TestCase):

    def setUp(self):
        from schoolbell.app.app import PersonContainer
        from schoolbell.app.rest.app import PersonFileFactory

        self.personContainer = PersonContainer()
        self.factory = PersonFileFactory(self.personContainer)

    def test_title(self):
        person = self.factory("new_person", None,
                     '''<object xmlns="http://schooltool.org/ns/model/0.1"
                                title="New Person"/>''')

        self.assertEquals(person.title, "New Person")


class TestGroupFile(unittest.TestCase):
    """A test for IGroup IWriteFile adapter"""

    def testWrite(self):
        group = Group("Lillies")

        file = GroupFile(group)
        file.write('''<object xmlns="http://schooltool.org/ns/model/0.1"
                              title="New Group"
                              description="Boo"/>''')

        self.assertEquals(group.title, "New Group")
        self.assertEquals(group.description, "Boo")


class TestResourceFile(unittest.TestCase):
    """A test for IResource IWriteFile adapter"""

    def testWrite(self):
        resource = Resource("Mud")

        file = ResourceFile(resource)
        file.write('''<object xmlns="http://schooltool.org/ns/model/0.1"
                              title="New Mud"
                              description="Baa"/>''')

        self.assertEquals(resource.title, "New Mud")
        self.assertEquals(resource.description, "Baa")


class TestPersonFile(unittest.TestCase):
    """A test for IPerson IWriteFile adapter"""

    def testWrite(self):
        person = Person("Frog")

        file = PersonFile(person)
        file.write('''<object xmlns="http://schooltool.org/ns/model/0.1"
                              title="Frogsworth"/>''')

        self.assertEquals(person.title, "Frogsworth")


class ApplicationObjectViewTestMixin(ContainerViewTestMixin):

    def setUp(self):
        ContainerViewTestMixin.setUp(self)

    def get(self):
        """Perform a GET of the view being tested."""
        view = self.makeTestView(self.testObject, TestRequest())
        result = view.GET()

        return result, view.request.response


class TestGroupView(ApplicationObjectViewTestMixin, unittest.TestCase):
    """A test for the RESTive view of a group."""

    def setUp(self):
        ApplicationObjectViewTestMixin.setUp(self)

        self.testObject = self.app['groups']['root'] = Group("Root group")

    def makeTestView(self, object, request):
        return GroupView(object, request)

    def testGET(self):

        result, response = self.get()
        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result,
            """<group xmlns:xlink="http://www.w3.org/1999/xlink">
                   <title>Root group</title>
                   <description/>
                   <relationships xlink:href="http://127.0.0.1/groups/root/relationships"
                                  xlink:title="Relationships" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/groups/root/acl" xlink:title="ACL"
                        xlink:type="simple"/>
                   <calendar xlink:href="http://127.0.0.1/groups/root/calendar"
                             xlink:title="Calendar" xlink:type="simple"/>
                   <relationships
                                  xlink:href="http://127.0.0.1/groups/root/calendar/relationships"
                                  xlink:title="Calendar subscriptions" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/groups/root/calendar/acl"
                        xlink:title="Calendar ACL" xlink:type="simple"/>
               </group>""")

    def testGETDescription(self):

        self.testObject.description = "Foo"

        result, response = self.get()

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result,
            """<group xmlns:xlink="http://www.w3.org/1999/xlink">
                   <title>Root group</title>
                   <description>Foo</description>
                   <relationships xlink:href="http://127.0.0.1/groups/root/relationships"
                                  xlink:title="Relationships" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/groups/root/acl" xlink:title="ACL"
                        xlink:type="simple"/>
                   <calendar xlink:href="http://127.0.0.1/groups/root/calendar"
                             xlink:title="Calendar" xlink:type="simple"/>
                   <relationships
                                  xlink:href="http://127.0.0.1/groups/root/calendar/relationships"
                                  xlink:title="Calendar subscriptions" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/groups/root/calendar/acl"
                        xlink:title="Calendar ACL" xlink:type="simple"/>
               </group>""")


class TestResourceView(ApplicationObjectViewTestMixin, unittest.TestCase):
    """A test for the RESTive view of a resource."""

    def setUp(self):
        ApplicationObjectViewTestMixin.setUp(self)

        self.testObject = self.app['resources']['root'] = Resource("Root resource")

    def makeTestView(self, object, request):
        return ResourceView(object, request)

    def testGET(self):
        """Tests the GET method of the view."""

        result, response = self.get()
        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result,
            """<resource xmlns:xlink="http://www.w3.org/1999/xlink">
                   <title>Root resource</title>
                   <description/>
                   <relationships xlink:href="http://127.0.0.1/resources/root/relationships"
                                  xlink:title="Relationships" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/resources/root/acl" xlink:title="ACL"
                        xlink:type="simple"/>
                   <calendar xlink:href="http://127.0.0.1/resources/root/calendar"
                             xlink:title="Calendar" xlink:type="simple"/>
                   <relationships
                                  xlink:href="http://127.0.0.1/resources/root/calendar/relationships"
                                  xlink:title="Calendar subscriptions" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/resources/root/calendar/acl"
                        xlink:title="Calendar ACL" xlink:type="simple"/>
               </resource>""")

    def testGETDescription(self):

        self.testObject.description = "Foo"

        result, response = self.get()

        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result,
            """<resource xmlns:xlink="http://www.w3.org/1999/xlink">
                   <title>Root resource</title>
                   <description>Foo</description>
                   <relationships xlink:href="http://127.0.0.1/resources/root/relationships"
                                  xlink:title="Relationships" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/resources/root/acl" xlink:title="ACL"
                        xlink:type="simple"/>
                   <calendar xlink:href="http://127.0.0.1/resources/root/calendar"
                             xlink:title="Calendar" xlink:type="simple"/>
                   <relationships
                                  xlink:href="http://127.0.0.1/resources/root/calendar/relationships"
                                  xlink:title="Calendar subscriptions" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/resources/root/calendar/acl"
                        xlink:title="Calendar ACL" xlink:type="simple"/>
               </resource>""")


class TestPersonView(ApplicationObjectViewTestMixin, unittest.TestCase):
    """A test for the RESTive view of a person."""

    def setUp(self):
        ApplicationObjectViewTestMixin.setUp(self)

        self.testObject = self.app['persons']['root'] = Person("root",
            title="Root person")

    def makeTestView(self, object, request):
        return PersonView(object, request)

    def testGET(self):

        result, response = self.get()
        self.assertEquals(response.getHeader('content-type'),
                          "text/xml; charset=UTF-8")
        self.assertEqualsXML(result,
            """<person xmlns:xlink="http://www.w3.org/1999/xlink">
                   <title>Root person</title>
                   <relationships xlink:href="http://127.0.0.1/persons/root/relationships"
                                  xlink:title="Relationships" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/persons/root/acl" xlink:title="ACL"
                        xlink:type="simple"/>
                   <calendar xlink:href="http://127.0.0.1/persons/root/calendar"
                             xlink:title="Calendar" xlink:type="simple"/>
                   <relationships
                                  xlink:href="http://127.0.0.1/persons/root/calendar/relationships"
                                  xlink:title="Calendar subscriptions" xlink:type="simple"/>
                   <acl xlink:href="http://127.0.0.1/persons/root/calendar/acl"
                        xlink:title="Calendar ACL" xlink:type="simple"/>
               </person>""")


class TestPersonPasswordWriter(unittest.TestCase):

    def testSetPassword(self):
        from schoolbell.app.rest.app import PersonPasswordWriter
        person =  Person("Frog")
        passwordWriter = PersonPasswordWriter(person)
        passwordWriter.setPassword("gorf")
        self.assert_(person.checkPassword("gorf"))

    def testConformance(self):
        from schoolbell.app.rest.app import PersonPasswordWriter
        from schoolbell.app.rest.interfaces import IPasswordWriter
        person =  Person("Frog")
        passwordWriter = PersonPasswordWriter(person)
        self.assert_(verifyObject(IPasswordWriter, passwordWriter))


class TestPersonPasswordWriterView(ApplicationObjectViewTestMixin,
                                   unittest.TestCase):

    def setUp(self):
        from schoolbell.app.rest.app import PersonPasswordWriter
        ApplicationObjectViewTestMixin.setUp(self)
        self.person = self.app['persons']['root'] = Person("root",
                                                           title="Root person")

        self.testObject = PersonPasswordWriter(self.person)

    def makeTestView(self, object, request):
        from schoolbell.app.rest.app import PasswordWriterView
        return PasswordWriterView(object, request)

    def testPUT(self):

        request = TestRequest(StringIO("super-secret-password"))
        view = self.makeTestView(self.testObject, request)
        result = view.PUT()
        response = request.response

        self.assertEquals(response.getStatus(), 200)
        self.assertEqualsXML(result, "")
        self.assert_(self.person.checkPassword("super-secret-password"))


class TestPersonPhotoAdapter(unittest.TestCase):

    def makeTestObject(self):

        from schoolbell.app.rest.app import PersonPhotoAdapter
        return PersonPhotoAdapter(Person("Frog"))

    def testConformance(self):

        from schoolbell.app.rest.interfaces import IPersonPhoto
        personPhoto = self.makeTestObject()
        self.assert_(verifyObject(IPersonPhoto, personPhoto))

    def testSetDeletePhoto(self):

        personPhoto = self.makeTestObject()
        personPhoto.writePhoto("lalala")
        self.assertEquals(personPhoto.person.photo, "lalala")

        personPhoto.deletePhoto()
        self.assert_(personPhoto.person.photo is None)

    def testGetPhoto(self):

        personPhoto = self.makeTestObject()
        personPhoto.writePhoto("lalala")
        self.assertEquals(personPhoto.getPhoto(), "lalala")

        personPhoto.deletePhoto()
        self.assert_(personPhoto.getPhoto() is None)


class TestPersonPhotoView(ApplicationObjectViewTestMixin,
                          unittest.TestCase):

    def setUp(self):

        from schoolbell.app.rest.app import PersonPhotoAdapter
        ApplicationObjectViewTestMixin.setUp(self)
        self.person = self.app['persons']['root'] = Person("root",
                                                           title="Root person")

        self.testObject = PersonPhotoAdapter(self.person)

    def makeTestView(self):

        from schoolbell.app.rest.app import PersonPhotoView
        return PersonPhotoView(self.testObject,
                               TestRequest(StringIO("Icky Picky")))

    def testGETNotFound(self):

        view = self.makeTestView()
        self.assertRaises(NotFound, view.GET)

    def testGET(self):

        view = self.makeTestView()
        view.PUT()
        result = view.GET()
        response = view.request.response

        self.assertEquals(response.getStatus(), 200)
        self.assertEquals(result, "Icky Picky")

    def testPUT(self):

        view = self.makeTestView()
        result = view.PUT()
        response = view.request.response

        self.assertEquals(response.getStatus(), 200)
        self.assertEquals(result, "")

    def testDelete(self):

        view = self.makeTestView()
        view.DELETE()

        self.assertRaises(NotFound, view.GET)


def doctest_PersonHttpTraverser():
    """Tests for PersonHttpTraverser.

    PersonHttpTraverser allows you to access photo and password of the
    person:

        >>> from schoolbell.app.rest.app import PersonHTTPTraverser
        >>> from schoolbell.app.app import Person
        >>> person = Person()
        >>> request = TestRequest()
        >>> traverser = PersonHTTPTraverser(person, request)
        >>> traverser.context is person
        True
        >>> traverser.request is request
        True

    The traverser should implement IBrowserPublisher:

        >>> from zope.publisher.interfaces.browser import IBrowserPublisher
        >>> verifyObject(IBrowserPublisher, traverser)
        True

    The traverser inherits from CalendarOwnerHttpTraverser so we
    should be able to access the calendar of his:

        >>> traverser.publishTraverse(request, 'calendar') is person.calendar
        True
        >>> traverser.publishTraverse(request, 'calendar.ics') is person.calendar
        True
        >>> traverser.publishTraverse(request, 'calendar.vfb') is person.calendar
        True

    As well as password:

        >>> traverser.publishTraverse(request, 'password')
        <schoolbell.app.rest.app.PersonPasswordWriter object at ...>

    and photo:

        >>> traverser.publishTraverse(request, 'photo')
        <schoolbell.app.rest.app.PersonPhotoAdapter object at ...>

    """

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(test) for test in
                    (TestAppView,
                     TestGroupContainerView,
                     TestResourceContainerView,
                     TestPersonContainerView,
                     TestGroupFileFactory,
                     TestResourceFileFactory,
                     TestPersonFileFactory,
                     TestGroupFile,
                     TestPersonFile,
                     TestResourceFile,
                     TestGroupView,
                     TestResourceView,
                     TestPersonView,
                     TestPersonPasswordWriter,
                     TestPersonPasswordWriterView,
                     TestPersonPhotoAdapter,
                     TestPersonPhotoView)])

    suite.addTest(doctest.DocTestSuite(optionflags=doctest.ELLIPSIS|
                                                   doctest.REPORT_NDIFF))
    suite.addTest(doctest.DocTestSuite('schoolbell.app.rest.app'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
