#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve31
"""
import unittest
import doctest

from zope.app.testing import setup
from zope.interface import implements
from zope.container import btree
from zope.component import provideHandler

from schooltool.relationship.tests import setUpRelationships
from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.person import BasicPerson
from schooltool.relationship.tests import URIStub
from schooltool.relationship.interfaces import IRelationshipLinks
from schooltool.relationship.interfaces import IRelationshipRemovedEvent
from schooltool.relationship.interfaces import IRelationshipAddedEvent
from schooltool.relationship.relationship import relate
from schooltool.contact.contact import URIContact, URIPerson


class AppStub(btree.BTreeContainer):
    implements(ISchoolToolApplication)


def printRelationshipAdded(event):
    print 'Relate (%s): %s with %s' % (
        event.rel_type, event[URIPerson].first_name, event[URIContact].first_name)


def printRelationshipRemoved(event):
    print 'Unrelate (%s): %s from %s' % (
        event.rel_type, event[URIPerson].first_name, event[URIContact].first_name)


def doctest_evolve31():
    """Evolution to generation 31.

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()

    Create a bunch of persons.

        >>> persons = app['persons'] = btree.BTreeContainer()
        >>> persons['will'] = BasicPerson("will", "William", "")
        >>> persons['vlad'] = BasicPerson("vlad", "Vladimir", "")
        >>> persons['john'] = BasicPerson("john", "Johny", "")
        >>> persons['pete'] = BasicPerson("pete", "Petey", "")
        >>> persons['bill'] = BasicPerson("bill", "Billy", "")

    Set up contacts.  In reality, contacts are instances of
    schooltool.contact.contact.Contact,  but we'll use BasicPerson as a stub.

        >>> def contact(person, contact, rel_type=URIContact):
        ...     relate(rel_type,
        ...            (person, URIPerson),
        ...            (contact, URIContact))

        >>> contact(persons['john'], persons['pete'])
        >>> contact(persons['john'], persons['bill'])
        >>> contact(persons['will'], persons['bill'])

    Add relationships that will not be evolved.

        >>> URIBoring = URIStub('Uninteresting relationship')
        >>> contact(persons['will'], persons['pete'], rel_type=URIBoring)

    Let's evolve now.

        >>> provideHandler(printRelationshipAdded,
        ...                [IRelationshipAddedEvent])
        >>> provideHandler(printRelationshipRemoved,
        ...                [IRelationshipRemovedEvent])

        >>> from schooltool.generations.evolve31 import evolve
        >>> evolve(context)
        Unrelate (<URIObject Contact>): Johny from Petey
        Relate (<URIObject Contact relationship>): Johny with Petey
        Unrelate (<URIObject Contact>): Johny from Billy
        Relate (<URIObject Contact relationship>): Johny with Billy
        Unrelate (<URIObject Contact>): William from Billy
        Relate (<URIObject Contact relationship>): William with Billy

    New relationships now have extra_info assigned.

        >>> links = IRelationshipLinks(persons['john']).getLinksByRole(URIContact)
        >>> for link in links:
        ...     print '%s %s: %s' % (
        ...         link.target.first_name, link.rel_type, link.extra_info)
        Petey <URIObject Contact relationship>:
          <schooltool.contact.contact.ContactPersonInfo object at ...>
        Billy <URIObject Contact relationship>:
          <schooltool.contact.contact.ContactPersonInfo object at ...>

    """


def setUp(test):
    setup.placelessSetUp()
    setup.setUpAnnotations()
    setUpRelationships()


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=optionflags)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
