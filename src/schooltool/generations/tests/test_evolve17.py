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
Unit tests for schooltool.generations.evolve17

$Id: test_evolve16.py 6212 2006-06-08 13:01:04Z vidas $
"""

import unittest

from zope.app.testing.setup import setUpAnnotations
from zope.annotation.interfaces import IAnnotatable
from zope.app.testing import setup
from zope.testing import doctest
from zope.interface import implements, directlyProvides
from zope.app.folder.folder import Folder
from zope.component.interfaces import IComponentLookup
from zope.app.intid.interfaces import IIntIds
from zope.app.catalog.interfaces import ICatalog

from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.demographics.person import Person


class AppStub(Folder):
    implements(ISchoolToolApplication, IAnnotatable)

    def __init__(self):
        super(AppStub, self).__init__()
        self['persons'] = {}

def doctest_evolve():
    r"""Doctest for evolution to generation 17.

      >>> context = ContextStub()
      >>> context.root_folder['app'] = app = AppStub()
      >>> dummy = setup.createSiteManager(app)
      >>> alpha = Person('alpha', 'Alpha')
      >>> alpha.schooldata.id = 'a'
      >>> beta = Person('beta', 'Beta')
      >>> beta.schooldata.id = 'b'
      >>> app['persons']['alpha'] = alpha
      >>> app['persons']['beta'] = beta

    Set the site:
      >>> from zope.app.component.hooks import setSite
      >>> setSite(app)

    Make the person searchable:

      >>> from zope.component import provideAdapter
      >>> from schooltool.demographics.utility import Search
      >>> from schooltool.demographics.interfaces import ISearch
      >>> from schooltool.person.interfaces import IPerson
      >>> provideAdapter(Search, [IPerson], ISearch)

    Do the evolution:

      >>> from schooltool.generations.evolve17 import evolve
      >>> evolve(context)

    We expect the utilities to be installed:

      >>> from zope.component import getUtility
      >>> utility = getUtility(IIntIds)
      >>> IIntIds.providedBy(utility)
      True
      >>> catalog = getUtility(ICatalog, 'demographics_catalog')
      >>> ICatalog.providedBy(catalog)
      True

    We also expect things to be indexed. Let's check the
    studentId fieldindex:

      >>> results = catalog.searchResults(studentId=('a', 'a'))
      >>> [item.title for item in results]
      ['Alpha']
      >>> results = catalog.searchResults(studentId=('b', 'b'))
      >>> [item.title for item in results]
      ['Beta']
      >>> results = catalog.searchResults(studentId=('c', 'c'))
      >>> [item.title for item in results]
      []

    Since the last name is required now but we don't know what
    last name people had, we expect to see 'Last name unknown':

      >>> app['persons']['alpha'].nameinfo.last_name
      'Last name unknown'

    """

from zope.app.keyreference.interfaces import IKeyReference


_d = {}


class StupidKeyReference(object):
    implements(IKeyReference)
    key_type_id = 'StupidKeyReference'
    def __init__(self, ob):
        global _d
        self.id = id(ob)
        _d[self.id] = ob
    def __call__(self):
        return _d[self.id]
    def __hash__(self):
        return self.id
    def __cmp__(self, other):
        return cmp(hash(self), hash(other))


def setUp(test):
    setup.placefulSetUp()
    setup.setUpTraversal()
    setUpAnnotations()

    # this is code to set up the catalog for unit testing. it could
    # be extracted and put into general setup functionality

    # Make sure objects can be keyreferenced - necessary for int ids to
    # work:

    from zope.component import provideAdapter
    from persistent.interfaces import IPersistent
    provideAdapter(StupidKeyReference, [IPersistent], IKeyReference)

    # Provide the int id subscribers:

    from zope.component import provideHandler
    from zope.app.intid import addIntIdSubscriber, removeIntIdSubscriber
    from zope.location.interfaces import ILocation
    from zope.app.container.interfaces import IObjectAddedEvent
    from zope.app.container.interfaces import IObjectRemovedEvent
    provideHandler(addIntIdSubscriber,
                   [ILocation, IObjectAddedEvent])
    provideHandler(removeIntIdSubscriber,
                   [ILocation, IObjectRemovedEvent])

    # And the catalog subscribers:

    from zope.app.catalog import catalog
    from zope.app.catalog.interfaces import ICatalogIndex
    from zope.app.intid.interfaces import IIntIdAddedEvent,\
         IIntIdRemovedEvent
    from zope.lifecycleevent.interfaces import IObjectModifiedEvent
    provideHandler(catalog.indexAdded,
                   [ICatalogIndex, IObjectAddedEvent])
    provideHandler(catalog.indexDocSubscriber,
                   [IIntIdAddedEvent])
    provideHandler(catalog.reindexDocSubscriber,
                   [IObjectModifiedEvent])
    provideHandler(catalog.unindexDocSubscriber,
                   [IIntIdRemovedEvent])

def tearDown(test):
    setup.placefulTearDown()


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
