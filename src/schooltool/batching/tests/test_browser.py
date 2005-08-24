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
Unit tests for schooltool.batching.browser

$Id$
"""

import unittest

from zope.testing import doctest

from zope.publisher.browser import TestRequest

def doctest_MultiBatchViewMixin():
    r"""Tests for MultiBatchViewMixin

    MultiBatchViewMixin makes it easy (or easier) to create a BrowserView
    composed of multiple batches.

        >>> data1 = [1, 2, 3, 4, 5]
        >>> data2 = [100, 200, 300, 400, 500]

        >>> from zope.app.publisher.browser import BrowserView
        >>> from schooltool.batching.browser import MultiBatchViewMixin

        >>> class SampleView(BrowserView, MultiBatchViewMixin):
        ...
        ...     def __init__(self, context, request):
        ...         BrowserView.__init__(self, context, request)
        ...         MultiBatchViewMixin.__init__(self, names=['first', 'second'])
        ...
        ...     def update(self):
        ...         # Do some kind of normal request processing
        ...         MultiBatchViewMixin.update(self)
        ...         self.updateBatch('first', data1)
        ...         self.updateBatch('second', data2)

    Without anything in the request, we get default batch start/size:

        >>> request = TestRequest()
        >>> view = SampleView(None, request)
        >>> view.update()
        >>> [i for i in view.batches['first']]
        [1, 2, 3, 4, 5]
        >>> [i for i in view.batches['second']]
        [100, 200, 300, 400, 500]

    Given a set of request values that correspond to batch names, we can
    navigate each batch independantly of the others

        >>> request.form = {'batch_start.first' : '2'}
        >>> view.update()
        >>> [i for i in view.batches['first']]
        [3, 4, 5]
        >>> [i for i in view.batches['second']]
        [100, 200, 300, 400, 500]

        >>> request.form = {'batch_start.first' : '0',
        ...                 'batch_size.first' : '2',
        ...                 'batch_start.second' : '2',
        ...                 'batch_size.second' : '3'}
        >>> view.update()

        >>> [i for i in view.batches['first']]
        [1, 2]
        >>> [i for i in view.batches['second']]
        [300, 400, 500]

    """

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(optionflags=doctest.ELLIPSIS))
    suite.addTest(doctest.DocTestSuite('schooltool.batching.browser'))
    suite.addTest(doctest.DocFileSuite('../README.txt',
                                        optionflags=doctest.ELLIPSIS|
                                                    doctest.REPORT_NDIFF))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
