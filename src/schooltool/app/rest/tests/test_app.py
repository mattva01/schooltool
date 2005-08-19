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
Unit tests for schooltool.app.rest.app.

$Id: test_app.py 3526 2005-04-28 17:16:47Z bskahan $
"""
import unittest

from zope.publisher.browser import TestRequest
from zope.testing import doctest
from zope.app.testing import setup

from schooltool.testing import setup as sbsetup


def doctest_ApplicationView():
    """SchoolToolApplication

    Lets create a schooltool instance and make a view for it:

        >>> from schooltool.app.rest.app import ApplicationView
        >>> setup.placefulSetUp()
        >>> app = sbsetup.setupSchoolToolSite()
        >>> view = ApplicationView(app, TestRequest())
        >>> result = view.GET()

    Lets test the XML output:

        >>> from schooltool.app.rest.xmlparsing import XMLDocument
        >>> doc = XMLDocument(result)
        >>> doc.registerNs('xlink', 'http://www.w3.org/1999/xlink')

    There should only be one set of containers:

        >>> nodes = doc.query('/schooltool/containers')
        >>> len(nodes)
        1

    Let's test our containers:

    persons:

        >>> persons = doc.query('/schooltool/containers/container'
        ...                     '[@xlink:href="http://127.0.0.1/persons"]')[0]
        >>> persons['xlink:type']
        u'simple'
        >>> persons['xlink:title']
        u'persons'

    groups:

        >>> groups = doc.query('/schooltool/containers/container'
        ...                     '[@xlink:href="http://127.0.0.1/groups"]')[0]
        >>> groups['xlink:type']
        u'simple'
        >>> groups['xlink:title']
        u'groups'

    resources:

        >>> resources = doc.query('/schooltool/containers/container'
        ...                     '[@xlink:href="http://127.0.0.1/resources"]')[0]
        >>> resources['xlink:type']
        u'simple'
        >>> resources['xlink:title']
        u'resources'

    sections:

        >>> sections = doc.query('/schooltool/containers/container'
        ...                     '[@xlink:href="http://127.0.0.1/sections"]')[0]
        >>> sections['xlink:type']
        u'simple'
        >>> sections['xlink:title']
        u'sections'

    courses:

        >>> courses = doc.query('/schooltool/containers/container'
        ...                     '[@xlink:href="http://127.0.0.1/courses"]')[0]
        >>> courses['xlink:type']
        u'simple'
        >>> courses['xlink:title']
        u'courses'

    that's all of our containers:

        >>> doc.free()

    XXX this is what our output should look like:

    """


def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite(optionflags=doctest.ELLIPSIS),
        doctest.DocTestSuite('schooltool.app.rest.app',
                             optionflags=doctest.ELLIPSIS),
        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
