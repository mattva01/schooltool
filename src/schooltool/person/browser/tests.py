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
Tests for Person views.
"""
import unittest
import doctest

from zope.publisher.browser import TestRequest

from schooltool.app.browser.testing import setUp, tearDown


def doctest_PersonPhotoView():
    r"""Test for PersonPhotoView

    We will need a person that has a photo:

        >>> from schooltool.person.person import Person
        >>> person = Person()
        >>> person.photo = "I am a photo!"

    We can now create a view:

        >>> from schooltool.person.browser.person import PersonPhotoView
        >>> request = TestRequest()
        >>> view = PersonPhotoView(person, request)

    The view returns the photo and sets the appropriate Content-Type header:

        >>> view()
        'I am a photo!'
        >>> request.response.getHeader("Content-Type")
        'image/jpeg'

    However, if a person has no photo, the view raises a NotFound error.

        >>> person.photo = None
        >>> view()                                  # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        NotFound: Object: <...Person object at ...>, name: u'photo'

    """


def doctest_PersonFilterWidget():
    """Doctest for PersonFilterWidget.

    For this test we will need a catalog with an index for person
    titles:

        >>> from zope.catalog.interfaces import ICatalog
        >>> class IndexStub(object):
        ...     def __init__(self):
        ...         self.documents_to_values = {}
        ...     def apply(self, query):
        ...         query = query.replace('*', '')
        ...         results = []
        ...         for id, value in self.documents_to_values.items():
        ...             if query in value:
        ...                 results.append(id)
        ...         return results
        >>> text_index = IndexStub()

        >>> class CatalogStub(dict):
        ...     def __init__(self):
        ...         self['text'] = text_index
        >>> catalog = CatalogStub()

   Some persons:

        >>> class PersonStub(object):
        ...     def __init__(self, title, groups, person_id):
        ...         self.id = person_id
        ...         self.title = title
        ...         self.__name__ = title
        ...         for group in groups:
        ...             group.add(self)
        ...     def __repr__(self):
        ...         return '<ItemStub %s>' % self.title

   Some groups:

        >>> class GroupStub(object):
        ...     def __init__(self, title):
        ...         self.title = title
        ...         self.members = []
        ...     def add(self, member):
        ...         self.members.append(member)
        >>> a = GroupStub('a')
        >>> b = GroupStub('b')
        >>> c = GroupStub('c')

   Container with some persons in it:

        >>> class ContainerStub(dict):
        ...     def __init__(self):
        ...         persons = [('a1234','alpha', [a]),
        ...                    ('a1235','beta', [b, c]),
        ...                    ('a1236','lambda', [b])]
        ...         for id, (username, title, groups) in enumerate(persons):
        ...             self[username] = PersonStub(title, groups, id)
        ...             text_index.documents_to_values[id] = ' '.join([title, username])
        ...     def __conform__(self, iface):
        ...         if iface == ICatalog:
        ...             return catalog

    Let's create the PersonFilterWidget:

        >>> from zope.publisher.browser import TestRequest
        >>> from schooltool.person.browser.person import PersonFilterWidget
        >>> container = ContainerStub()
        >>> request = TestRequest()
        >>> widget = PersonFilterWidget(container, request)

    The state of the widget (whether it will filter the data or not)
    is determined by checking whether there is at least one query
    parameter in the request:

        >>> widget.active()
        False

        >>> request.form = {'SEARCH_TITLE': 'lamb'}
        >>> widget.active()
        True

        >>> request.form = {'SEARCH_GROUP': 'lamb'}
        >>> widget.active()
        True

    The information that we got from the request can be appended to
    the url:

        >>> widget.extra_url()
        '&SEARCH_GROUP=lamb'

        >>> request.form = {'SEARCH_TITLE': 'lamb', 'SEARCH_GROUP': 'a'}
        >>> widget.extra_url()
        '&SEARCH_TITLE=lamb&SEARCH_GROUP=a'

    Filtering is done by skipping any entry that doesn't contain the
    query string in it's title, or are not in the target group:

        >>> from schooltool.app.interfaces import ISchoolToolApplication
        >>> from zope.component import adapts
        >>> from zope.interface import implements, Interface
        >>> class StubApplication(dict):
        ...     implements(ISchoolToolApplication)
        ...     adapts(Interface)
        ...     def __init__(self, context):
        ...         self['groups'] = {'a': a, 'b': b, 'c': c}
        >>> from zope.component import provideAdapter
        >>> provideAdapter(StubApplication)
        >>> from schooltool.group.interfaces import IGroupContainer
        >>> provideAdapter(lambda app: app['groups'],
        ...                adapts=[ISchoolToolApplication],
        ...                provides=IGroupContainer)

        >>> items = [{'id': 0},
        ...          {'id': 1},
        ...          {'id': 2}]

        >>> request.form = {'SEARCH_TITLE': 'lamb'}
        >>> widget.filter(items)
        [{'id': 2}]

        >>> from zope.component import provideUtility
        >>> from zope.intid.interfaces import IIntIds
        >>> class IntIdsStub(object):
        ...     def queryId(self, obj):
        ...         return obj.id
        >>> provideUtility(IntIdsStub(), IIntIds)

        >>> request.form = {'SEARCH_GROUP': 'b'}
        >>> widget.filter(items)
        [{'id': 1}, {'id': 2}]

        >>> request.form = {'SEARCH_GROUP': 'b',
        ...                 'SEARCH_TITLE': 'bet'}
        >>> widget.filter(items)
        [{'id': 1}]

   The search is case insensitive:

        >>> request.form = {'SEARCH_TITLE': 'AlphA'}
        >>> widget.filter(items)
        [{'id': 0}]

   The search also searches through usernames:

        >>> request.form = {'SEARCH_TITLE': '1234'}
        >>> widget.filter(items)
        [{'id': 0}]

    If clear search button is clicked, the form attribute is cleared,
    and all items are displayed:

        >>> request.form['CLEAR_SEARCH'] = 'Yes'

        >>> widget.filter(items)
        [{'id': 0}, {'id': 1}, {'id': 2}]
        >>> request.form['SEARCH_TITLE']
        ''

        >>> request.form['SEARCH_GROUP']
        ''

    """

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(
        setUp=setUp, tearDown=tearDown,
        optionflags=doctest.ELLIPSIS|doctest.REPORT_NDIFF))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
