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
Tests for person REST views.

$Id: test_app.py 4342 2005-07-25 16:02:24Z bskahan $
"""
import unittest
from cStringIO import StringIO

from zope.interface.verify import verifyObject
from zope.publisher.browser import TestRequest
from zope.publisher.interfaces import NotFound
from zope.testing import doctest
from zope.app.filerepresentation.interfaces import IFileFactory
from zope.app.testing import ztapi, setup

from schooltool.app.rest.testing import ApplicationObjectViewTestMixin
from schooltool.app.rest.testing import ContainerViewTestMixin
from schooltool.app.rest.testing import FileFactoriesSetUp
from schooltool.person.interfaces import IPersonContainer
from schooltool.person.person import PersonContainer, Person
from schooltool.person.rest.interfaces import IPasswordWriter
from schooltool.person.rest.interfaces import IPersonPhoto
from schooltool.person.rest.person import PersonContainerView, PersonView
from schooltool.person.rest.person import PersonPasswordWriter
from schooltool.person.rest.person import PersonPhotoAdapter
from schooltool.person.rest.person import PersonPhotoView
from schooltool.person.rest.person import PersonFile, PersonFileFactory
from schooltool.person.rest.person import PasswordWriterView
from schooltool.person.rest.preference import PersonPreferencesView


class TestPersonContainerView(ContainerViewTestMixin,
                             unittest.TestCase):
    """Test for PersonContainerView"""

    def setUp(self):
        ContainerViewTestMixin.setUp(self)
        ztapi.provideAdapter(IPersonContainer, IFileFactory,
                             PersonFileFactory)

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


class TestPersonFileFactory(unittest.TestCase):

    def setUp(self):
        self.personContainer = PersonContainer()
        self.factory = PersonFileFactory(self.personContainer)

    def test_title(self):
        person = self.factory("new_person", None,
                     '''<object xmlns="http://schooltool.org/ns/model/0.1"
                                title="New Person"/>''')

        self.assertEquals(person.title, "New Person")


class TestPersonFile(FileFactoriesSetUp, unittest.TestCase):
    """A test for IPerson IWriteFile adapter"""

    def setUp(self):
        FileFactoriesSetUp.setUp(self)
        ztapi.provideAdapter(IPersonContainer, IFileFactory,
                             PersonFileFactory)


    def testWrite(self):
        pc = PersonContainer()
        person = Person("Frog")
        pc['frog'] = person

        file = PersonFile(person)
        file.write('''<object xmlns="http://schooltool.org/ns/model/0.1"
                              title="Frogsworth"/>''')

        self.assertEquals(person.title, "Frogsworth")


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
        person =  Person("Frog")
        passwordWriter = PersonPasswordWriter(person)
        passwordWriter.setPassword("gorf")
        self.assert_(person.checkPassword("gorf"))

    def testConformance(self):
        person =  Person("Frog")
        passwordWriter = PersonPasswordWriter(person)
        self.assert_(verifyObject(IPasswordWriter, passwordWriter))


class TestPersonPasswordWriterView(ApplicationObjectViewTestMixin,
                                   unittest.TestCase):

    def setUp(self):
        ApplicationObjectViewTestMixin.setUp(self)
        self.person = self.app['persons']['root'] = Person("root",
                                                           title="Root person")

        self.testObject = PersonPasswordWriter(self.person)

    def makeTestView(self, object, request):
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
        return PersonPhotoAdapter(Person("Frog"))

    def testConformance(self):
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
        ApplicationObjectViewTestMixin.setUp(self)
        self.person = self.app['persons']['root'] = Person("root",
                                                           title="Root person")

        self.testObject = PersonPhotoAdapter(self.person)

    def makeTestView(self):
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
        self.assertEqual(result, "Icky Picky")

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


def doctest_PersonPasswordHttpTraverser():
    r"""Tests for PersonPasswordHTTPTraverser.

    This traverser allows you to access the password of the person:

        >>> from schooltool.person.rest.person import \
        ...     PersonPasswordHTTPTraverser
        >>> person = Person()
        >>> request = TestRequest()

        >>> traverser = PersonPasswordHTTPTraverser(person, request)
        >>> traverser.context is person
        True
        >>> traverser.request is request
        True

    The traverser should implement IHTTPPublisher:

        >>> from zope.publisher.interfaces.http import IHTTPPublisher
        >>> verifyObject(IHTTPPublisher, traverser)
        True

    Now access the password:

        >>> traverser.publishTraverse(request, 'password')
        <schooltool.person.rest.person.PersonPasswordWriter ...>
    """


def doctest_PersonPhotoHttpTraverser():
    r"""Tests for PersonPhotoHTTPTraverser.

    This traverser allows you to access the photo of the person:

        >>> from schooltool.person.rest.person import \
        ...     PersonPhotoHTTPTraverser
        >>> person = Person()
        >>> request = TestRequest()

        >>> traverser = PersonPhotoHTTPTraverser(person, request)
        >>> traverser.context is person
        True
        >>> traverser.request is request
        True

    The traverser should implement IHTTPPublisher:

        >>> from zope.publisher.interfaces.http import IHTTPPublisher
        >>> verifyObject(IHTTPPublisher, traverser)
        True

    Now access the password:

        >>> traverser.publishTraverse(request, 'photo')
        <schooltool.person.rest.person.PersonPhotoAdapter ...>
    """


def doctest_PersonPreferencesHttpTraverser():
    r"""Tests for PersonPreferencesHTTPTraverser.

    PersonPreferencesHTTPTraverser allows you to access the preferences of the
    person:

        >>> from schooltool.person.rest.preference import \
        ...     PersonPreferencesHTTPTraverser
        >>> person = Person()
        >>> request = TestRequest()

        >>> from schooltool.person.preference import getPersonPreferences
        >>> from schooltool.person.interfaces import IPersonPreferences
        >>> setup.placelessSetUp()
        >>> setup.setUpAnnotations()
        >>> ztapi.provideAdapter(Person, IPersonPreferences,
        ...                      getPersonPreferences)

        >>> traverser = PersonPreferencesHTTPTraverser(person, request)
        >>> traverser.context is person
        True
        >>> traverser.request is request
        True

    The traverser should implement IHTTPPublisher:

        >>> from zope.publisher.interfaces.http import IHTTPPublisher
        >>> verifyObject(IHTTPPublisher, traverser)
        True

    Now access the preferences:

        >>> traverser.publishTraverse(request, 'preferences')
        <schooltool.person.rest.preference.PersonPreferencesAdapter ...>

    Clean up:

        >>> setup.placelessTearDown()

    """


def doctest_PersonPreferencesView():
    r"""Tests for PersonPreferencesView.

    First lets create a view:

        >>> from schooltool.person.rest.preference import \
        ...     PersonPreferencesHTTPTraverser
        >>> from schooltool.person.preference import getPersonPreferences
        >>> from schooltool.person.interfaces import IPersonPreferences
        >>> setup.placefulSetUp()
        >>> ztapi.provideAdapter(Person, IPersonPreferences,
        ...                      getPersonPreferences)

        >>> person = Person()
        >>> traverser = PersonPreferencesHTTPTraverser(person, TestRequest())
        >>> adapter = traverser.publishTraverse(TestRequest(), 'preferences')
        >>> view = PersonPreferencesView(adapter, TestRequest())

        >>> print view.GET()
        <preferences xmlns:xlink="http://www.w3.org/1999/xlink">
        <BLANKLINE>
          <preference id="timezone" value="UTC"/>
          <preference id="timeformat" value="%H:%M"/>
          <preference id="dateformat" value="%Y-%m-%d"/>
          <preference id="weekstart" value="0"/>
        <BLANKLINE>
        </preferences>
        <BLANKLINE>

    Set a preference:

        >>> from StringIO import StringIO
        >>> body = '<preferences xmlns="http://schooltool.org/ns/model/0.1">' \
        ...        '  <preference id="timezone" value="US/Eastern"/>' \
        ...        '</preferences>'

        >>> view = PersonPreferencesView(adapter, TestRequest(StringIO(body)))
        >>> view.PUT()
        'Preferences updated'

    Check that the preference was set:

        >>> u'<preference id="timezone" value="US/Eastern"/>' in view.GET()
        True

    Attempting to set a preference that does not exist will raise an error:

        >>> body = '<preferences xmlns="http://schooltool.org/ns/model/0.1">' \
        ...        '  <preference id="fakepref" value="1"/>' \
        ...        '</preferences>'

        >>> view = PersonPreferencesView(adapter, TestRequest(StringIO(body)))
        >>> view.PUT()
        Traceback (most recent call last):
        ...
        RestError: Preference "fakepref" unknown

    Attempting to set a preference to an invalid value will also raise an
    error:

        >>> body = '<preferences xmlns="http://schooltool.org/ns/model/0.1">' \
        ...        '  <preference id="timezone" value="Tatooine/Mos Isley"/>' \
        ...        '</preferences>'

        >>> view = PersonPreferencesView(adapter, TestRequest(StringIO(body)))
        >>> view.PUT()
        Traceback (most recent call last):
        ...
        RestError: Preference value "Tatooine/Mos Isley" does not pass validation on "timezone"

    Clean up:

        >>> setup.placelessTearDown()

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(test) for test in
                    (TestPersonContainerView,
                     TestPersonFileFactory,
                     TestPersonFile,
                     TestPersonView,
                     TestPersonPasswordWriter,
                     TestPersonPasswordWriterView,
                     TestPersonPhotoAdapter,
                     TestPersonPhotoView)])

    suite.addTest(doctest.DocTestSuite(
        optionflags=doctest.ELLIPSIS|
                    doctest.REPORT_NDIFF|
                    doctest.REPORT_ONLY_FIRST_FAILURE)
        )
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
