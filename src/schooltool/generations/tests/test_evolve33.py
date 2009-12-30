#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve32
"""
import unittest

from zope.testing import doctest
from zope.app.testing import setup

from zope.component import queryUtility, provideUtility
from zope.component import provideAdapter
from zope.interface import implements
from zope.app import intid
from zope.app.folder import Folder
from zope.app.catalog.interfaces import ICatalog
from zope.app.container import btree
from zope.site.hooks import getSite, setSite

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.generations.tests import ContextStub
from schooltool.contact.basicperson import getBoundContact
from schooltool.contact.interfaces import IContact
from schooltool.contact.interfaces import IUniqueFormKey
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.basicperson.person import BasicPerson


class AppStub(Folder):
    implements(ISchoolToolApplication)

    def __init__(self):
        super(AppStub, self).__init__()
        self['persons'] = btree.BTreeContainer()
        self['persons']['john'] = BasicPerson("john", "Johny", "John")
        self['persons']['pete'] = BasicPerson("pete", "Petey", "Pete")


def verboseGetBoundContact(context):
    print 'IContact(<%s>)' % context.first_name
    return getBoundContact(context)



def doctest_evolve33():
    """Test evolution to generation 33.

    We'll need int ids.

        >>> provideUtility(intid.IntIds(), intid.interfaces.IIntIds)

    Also an adapter to obtain the contact, and adapter to create form keys.

        >>> provideAdapter(verboseGetBoundContact, [IBasicPerson], IContact)
        >>> provideAdapter(lambda obj: obj.__name__, [None], IUniqueFormKey)

    And of course the app.

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()
        >>> manager = setup.createSiteManager(app)

    Let's evolve now.  Note that persons get adapted to IContact.

        >>> from schooltool.generations.evolve33 import evolve
        >>> evolve(context)
        IContact(<Johny>)
        IContact(<Petey>)

    Site was restored after evolution.

        >>> print getSite()
        None

    Contact catalog was registered for ISchoolToolApplication sites.

        >>> catalog = queryUtility(ICatalog, 'schooltool.contact')
        >>> print catalog
        None

        >>> setSite(app)

        >>> catalog = queryUtility(ICatalog, 'schooltool.contact')
        >>> catalog
        <zc.catalog.extentcatalog.Catalog object ...>

    Catalog indexes were set up properly.

        >>> sorted(i.__name__ for i in catalog.values())
        [u'first_name', u'form_keys', u'last_name']

    And contacts of existing persons got indexed.

        >>> sorted(catalog['first_name'].documents_to_values.values())
        ['Johny', 'Petey']

    """


from schooltool.generations.tests import catalogSetUp, catalogTearDown


def setUp(test):
    catalogSetUp(test)
    setup.setUpDependable()
    setSite()

def tearDown(test):
    setSite()
    catalogTearDown(test)


def test_suite():
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=optionflags)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
