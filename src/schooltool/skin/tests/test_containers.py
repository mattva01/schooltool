#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Tests for schooltool.app.browser.containers.
"""
import unittest
import doctest

from zope.app.testing import setup
from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest

from schooltool.app.browser.testing import setUp, tearDown


def doctest_ContainerView():
    r"""Test for ContainerView

    Let's create some persons to toy with in a person container:

        >>> from schooltool.skin.containers import ContainerView
        >>> from schooltool.person.person import Person, PersonContainer
        >>> setup.setUpAnnotations()

        >>> personContainer = PersonContainer()
        >>> from zope.traversing.interfaces import IContainmentRoot
        >>> directlyProvides(personContainer, IContainmentRoot)

        >>> personContainer['pete'] = Person('pete', 'Pete Parrot')
        >>> personContainer['john'] = Person('john', 'Long John')
        >>> personContainer['frog'] = Person('frog', 'Frog Man')
        >>> personContainer['toad'] = Person('toad', 'Taodsworth')
        >>> request = TestRequest()
        >>> view = ContainerView(personContainer, request)

    After calling update, we should have a batch setup with everyone in it:

        >>> view.update()
        >>> [p.title for p in view.batch]
        ['Frog Man', 'Long John', 'Pete Parrot', 'Taodsworth']


    We can alter the batch size and starting point through the request

        >>> request.form = {'batch_start': '2',
        ...                 'batch_size': '2'}
        >>> view.update()
        >>> [p.title for p in view.batch]
        ['Pete Parrot', 'Taodsworth']

    We can search through the request:

        >>> request.form = {'SEARCH': 'frog'}
        >>> view.update()
        >>> [p.title for p in view.batch]
        ['Frog Man']

    And we can clear the search (which ignores any search value):

        >>> request.form = {'SEARCH': 'frog',
        ...                 'CLEAR_SEARCH': 'on'}
        >>> view.update()
        >>> [p.title for p in view.batch]
        ['Frog Man', 'Long John', 'Pete Parrot', 'Taodsworth']

    """


def doctest_ContainerDeleteView():
    r"""Test for ContainerDeleteView

    Let's create some persons to delete from a person container:

        >>> from schooltool.skin.containers import ContainerDeleteView
        >>> from schooltool.person.person import Person, PersonContainer
        >>> setup.setUpAnnotations()

        >>> personContainer = PersonContainer()

        >>> from zope.traversing.interfaces import IContainmentRoot
        >>> directlyProvides(personContainer, IContainmentRoot)

        >>> personContainer['pete'] = Person('pete', 'Pete Parrot')
        >>> personContainer['john'] = Person('john', 'Long John')
        >>> personContainer['frog'] = Person('frog', 'Frog Man')
        >>> personContainer['toad'] = Person('toad', 'Taodsworth')
        >>> request = TestRequest()
        >>> view = ContainerDeleteView(personContainer, request)

    We should have the list of all the Ids of items that are going to
    be deleted from container:

        >>> view.listIdsForDeletion()
        []

    We must pass ids of selected people in the request:

        >>> request.form = {'delete.pete': 'on',
        ...                 'delete.john': 'on',
        ...                 'CONFIRM': 'Confirm'}
        >>> ids = [key for key in view.listIdsForDeletion()]
        >>> ids.sort()
        >>> ids
        [u'john', u'pete']
        >>> [item.title for item in view.itemsToDelete]
        ['Long John', 'Pete Parrot']

    These two should be gone after update:

        >>> view.update()
        >>> ids = [key for key in personContainer]
        >>> ids.sort()
        >>> ids
        [u'frog', u'toad']

    And we should be redirected to the container view:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    If we press Cancel no one should get hurt though:

        >>> request.form = {'delete.frog': 'on',
        ...                 'delete.toad': 'on',
        ...                 'CANCEL': 'Cancel'}

    You see, both our firends are still in there:

        >>> ids = [key for key in personContainer]
        >>> ids.sort()
        >>> ids
        [u'frog', u'toad']

    But we should be redirected to the container:

        >>> request.response.getStatus()
        302
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    No redirection if nothing was pressed should happen:

        >>> request.form = {'delete.frog': 'on',
        ...                 'delete.toad': 'on'}
        >>> view.update()
        >>> request.response.getHeader('Location')
        'http://127.0.0.1'

    """


def doctest_TableContainerView():
    r"""Test for ContainerView

    Let's create some persons to toy with in a table container:

        >>> from schooltool.skin.containers import TableContainerView
        >>> from schooltool.person.person import Person, PersonContainer
        >>> setup.setUpAnnotations()

        >>> personContainer = PersonContainer()
        >>> from zope.traversing.interfaces import IContainmentRoot
        >>> directlyProvides(personContainer, IContainmentRoot)

        >>> personContainer['pete'] = Person('pete', 'Pete Parrot')
        >>> personContainer['john'] = Person('john', 'Long John')
        >>> personContainer['frog'] = Person('frog', 'Frog Man')
        >>> personContainer['toad'] = Person('toad', 'Taodsworth')
        >>> request = TestRequest()

    The table view is using the ITableFormatter adapter to lookup the
    approrpiate table formatter for the container:

        >>> from zope.component import provideAdapter
        >>> from schooltool.table.interfaces import ITableFormatter
        >>> from zope.interface import implements
        >>> class TableFormatter(object):
        ...     implements(ITableFormatter)
        ...     def __init__(self, context, request):
        ...         self.request = request
        ...     def setUp(self, **kwargs):
        ...         print "Setting up table formatter: %s" % kwargs

        >>> from schooltool.person.interfaces import IPersonContainer
        >>> from zope.publisher.interfaces.browser import IBrowserRequest
        >>> provideAdapter(TableFormatter, adapts=[IPersonContainer,
        ...                                        IBrowserRequest],
        ...                                provides=ITableFormatter)

    By default the template that displays a list of items is being
    used:

        >>> view = TableContainerView(personContainer, request)
        >>> view.canModify = lambda: False
        >>> view.template = lambda: "The table template."
        >>> view.delete_template = lambda: "The delete template."
        >>> result = view()
        Setting up table formatter:
         {'columns_before': [],
          'formatters': [<function url_cell_formatter at ...>]}

        >>> result
        'The table template.'

    If we can modify the list that is being displayed, an additional
    columns is added before the default columns:

        >>> view.canModify = lambda: True
        >>> result = view()
        Setting up table formatter:
            {'columns_before': [<....DependableCheckboxColumn object at ...>],
             'formatters': [<function url_cell_formatter at ...>]}

        >>> result
        'The table template.'


    If there 'DELETE' button is pressed, a different template is used:

        >>> request.form = {'delete.pete': 'on', 'DELETE': 'Delete'}
        >>> view()
        'The delete template.'

    We should have the list of all the Ids of items that are going to
    be deleted from container:

        >>> view.listIdsForDeletion()
        [u'pete']

    We must pass ids of selected people in the request:

        >>> request.form = {'delete.pete': 'on',
        ...                 'delete.john': 'on',
        ...                 'CONFIRM': 'Confirm'}
        >>> ids = [key for key in view.listIdsForDeletion()]
        >>> ids.sort()
        >>> ids
        [u'john', u'pete']
        >>> [item.title for item in view.itemsToDelete]
        ['Long John', 'Pete Parrot']

    These two should be gone after update:

        >>> view.update()
        Setting up table formatter:
            {'columns_before': [<...DependableCheckboxColumn ...>],
             'formatters': [<function url_cell_formatter ...>]}
        >>> ids = [key for key in personContainer]
        >>> ids.sort()
        >>> ids
        [u'frog', u'toad']

    If we press Cancel no one should get hurt though:

        >>> request.form = {'delete.frog': 'on',
        ...                 'delete.toad': 'on',
        ...                 'CANCEL': 'Cancel'}

    You see, both our firends are still in there:

        >>> ids = [key for key in personContainer]
        >>> ids.sort()
        >>> ids
        [u'frog', u'toad']

    """


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF
                   | doctest.REPORT_ONLY_FIRST_FAILURE
                   | doctest.NORMALIZE_WHITESPACE)
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=optionflags))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
