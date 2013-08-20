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
Unit tests for schooltool.person.person.
"""
import unittest
import doctest

from zope.interface.verify import verifyObject
from zope.app.testing import setup

from schooltool.person.person import PersonPasswordWriter
from schooltool.person.interfaces import IPasswordWriter

from schooltool.testing import setup as sbsetup


def doctest_PersonContainer():
    """Tests for PersonContainer

        >>> from schooltool.person.interfaces import IPersonContainer
        >>> from schooltool.person.person import PersonContainer
        >>> c = PersonContainer()
        >>> verifyObject(IPersonContainer, c)
        True

    PersonContainer uses the `username` attribute of persons as the key

        >>> from schooltool.person.person import Person
        >>> person = Person(username="itsme")
        >>> c['doesnotmatter'] = person
        >>> c['itsme'] is person
        True
        >>> c.get('doesnotmatter') is None
        True

    Adaptation (i.e. __conform__) is tested in doctest_SchoolToolApplication.
    """


def doctest_Person():
    r"""Tests for Person

        >>> from schooltool.person.interfaces import IPersonContained
        >>> from schooltool.person.person import Person
        >>> person = Person('person')
        >>> verifyObject(IPersonContained, person)
        True

    Persons initially have no password

        >>> person.hasPassword()
        False

    When a person has no password, he cannot log in

        >>> person.checkPassword('')
        False
        >>> person.checkPassword(None)
        False

    You can set the password

        >>> person.setPassword('secret')
        >>> person.hasPassword()
        True
        >>> person.checkPassword('secret')
        True
        >>> person.checkPassword('justguessing')
        False

    Note that the password is not stored in plain text and cannot be recovered

        >>> import pickle
        >>> 'secret' not in pickle.dumps(person)
        True

    You can lock out the user's accound by setting the password to None

        >>> person.setPassword(None)
        >>> person.hasPassword()
        False
        >>> person.checkPassword('')
        False
        >>> person.checkPassword(None)
        False

    Note that you can set the password to an empty string, although that is
    not a secure password

        >>> person.setPassword('')
        >>> person.hasPassword()
        True
        >>> person.checkPassword('')
        True
        >>> person.checkPassword(None)
        False

    It is probably not a very good idea to use non-ASCII characters in
    passwords, but you can do that

        >>> person.setPassword(u'\u1234')
        >>> person.checkPassword(u'\u1234')
        True

    Persons are comparable (by username):

        >>> person == person
        True
        >>> person == Person('person')
        True
        >>> person == 'foo'
        False

    Persons have a calendar:

        >>> setup.placelessSetUp()
        >>> setup.setUpAnnotations()
        >>> sbsetup.setUpCalendaring()

        >>> from schooltool.app.interfaces import ISchoolToolCalendar
        >>> calendar = ISchoolToolCalendar(person)
        >>> calendar.__name__
        'calendar'
        >>> calendar.__parent__ is person
        True
        >>> len(calendar)
        0

    Clean up:

        >>> setup.placelessTearDown()

    """


def doctest_PersonPreferences():
    r"""Tests for the Preferences adapter

        >>> from zope.app.testing import setup
        >>> setup.placelessSetUp()
        >>> setup.setUpAnnotations()
        >>> from schooltool.person.person import Person

        >>> person = Person('person')

    Note that the ``IHavePreferences`` interface is added in ZCML.

    Make sure the attribute stores the correct interface

        >>> from schooltool.person.interfaces import IPersonPreferences
        >>> from schooltool.person.preference import getPersonPreferences
        >>> prefs = getPersonPreferences(person)
        >>> verifyObject(IPersonPreferences, prefs)
        True

        >>> prefs
        <schooltool.person.preference.PersonPreferences object at 0x...>

        >>> prefs.cal_periods
        True

    Need to have prefs.__parent__ refer to the person it's attached to:

        >>> prefs.__parent__ == person
        True

    Called another time, getPersonPreferences() returns the same object:

        >>> getPersonPreferences(person) is prefs
        True

    Clean up:

        >>> setup.placelessTearDown()

    """


class TestPersonPasswordWriter(unittest.TestCase):

    def testSetPassword(self):
        from schooltool.person.person import Person
        person =  Person("Frog")
        passwordWriter = PersonPasswordWriter(person)
        passwordWriter.setPassword("gorf")
        self.assert_(person.checkPassword("gorf"))

    def testConformance(self):
        from schooltool.person.person import Person
        person =  Person("Frog")
        passwordWriter = PersonPasswordWriter(person)
        self.assert_(verifyObject(IPasswordWriter, passwordWriter))


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
        doctest.DocTestSuite('schooltool.person.person'),
        unittest.makeSuite(TestPersonPasswordWriter)
        ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
