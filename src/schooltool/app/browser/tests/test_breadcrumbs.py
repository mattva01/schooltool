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
"""Breadcrumbs tests

$Id$
"""
__docformat__ = 'reStructuredText'
import unittest
from zope.testing import doctest, doctestunit
from schooltool.app.browser.testing import setUp, tearDown

def test_breadcrumbs():
    """
    Breadcrumbs
    -----------

    The SchoolTool breadcrumb mechanism uses breadcrumb info objects to
    retrieve its data. Those info objects have a ``name``, ``url`` and
    ``active`` attribute. The name is the name displayed in the
    breadcrumbs. The URL is the one used for the link of the crumb. Finally,
    the ``active`` flag specifies whether a link should be provided for the
    crumb or not.

    The default implementation is called ``GenericBreadcrumbInfo``. Here is
    how it works.

      >>> class Object(object):
      ...     def __init__(self, parent=None, name=None):
      ...         self.__parent__ = parent
      ...         self.__name__ = name

      >>> root = Object()
      >>> from zope.app.traversing.interfaces import IContainmentRoot
      >>> import zope.interface
      >>> zope.interface.directlyProvides(root, IContainmentRoot)

      >>> sub1 = Object(root, 'sub1')

      >>> from zope.publisher.browser import TestRequest
      >>> request = TestRequest()

    Now we can initialize the genreic info adapter:

      >>> from schooltool.app.browser import breadcrumbs
      >>> generic = breadcrumbs.GenericBreadcrumbInfo(sub1, request)

    The generic ``active`` flag value is always true:

      >>> generic.active
      True

    The URL is just the absolute URL:

      >>> generic.url
      'http://127.0.0.1/sub1'

    The name is constructed in a more complex manner. First, it looks for a
    title attribute; if none is found, it uses the containment name:

      >>> generic.name
      'sub1'
      >>> sub1.title = 'Sub-Object 1'
      >>> generic.name
      'Sub-Object 1'

    If the object is a containment root and no name or title is set, the word
    "top" is returned:

      >>> generic_root = breadcrumbs.GenericBreadcrumbInfo(root, request)
      >>> generic_root.name
      u'top'

    Now, a common use case is to specify a custom name for the breadcrumbs. In
    those cases you simply create a class as follows:

      >>> MyNameInfo = breadcrumbs.CustomNameBreadCrumbInfo('My Name')
      >>> info = MyNameInfo(sub1, request)
      >>> info.name
      'My Name'

    Let's now register the breadcrumb info as an adapter:

      >>> import zope.component
      >>> import zope.interface
      >>> from schooltool.app.browser import interfaces
      >>> zope.component.provideAdapter(breadcrumbs.GenericBreadcrumbInfo,
      ...                              (Object, TestRequest),
      ...                              interfaces.IBreadcrumbInfo)

    We can now get the entire breadcrumb info:

      >>> crumbs = breadcrumbs.Breadcrumbs(sub1, request)
      >>> pprint(list(crumbs.crumbs))
      [{'active': True,
        'name': u'top',
        'url': 'http://127.0.0.1'},
       {'active': True,
        'name': 'Sub-Object 1',
        'url': 'http://127.0.0.1/sub1'}]
    """


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF
                   | doctest.REPORT_ONLY_FIRST_FAILURE)
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       globs={'pprint': doctestunit.pprint},
                                       optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
