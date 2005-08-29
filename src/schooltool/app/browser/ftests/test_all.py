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
Functional tests for schooltool.app.app.

$Id: test_all.py 2922 2005-02-22 19:04:44Z mg $
"""

import os
import unittest

from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.testing import doctest
from zope.app.publisher.browser import BrowserView
from zope.app.testing.functional import FunctionalTestSetup
from zope.app.testing.functional import FunctionalDocFileSuite

from schooltool.testing import analyze

class BrokenView(BrowserView):
    implements(IBrowserPublisher)

    def browserDefault(self, request):
        return self, ()

    def publishTraverse(self, name, request):
        raise LookupError(name)

    def __call__(self):
        raise RuntimeError("Houston, we've got a problem")



def find_ftesting_zcml():
    """Find ftesting.zcml in the closest parent directory."""
    dir = os.path.abspath(os.path.dirname(__file__))
    while True:
        filename = os.path.join(dir, 'ftesting.zcml')
        if os.path.exists(filename):
            return filename
        dir = os.path.dirname(dir)
        if dir == os.path.dirname(dir): # we're looping at the filesystem root
            raise RuntimeError("I can't find ftesting.zcml!")


def test_suite():
    # Find SchoolTool's ftesting.zcml and load it.
    try:
        FunctionalTestSetup(find_ftesting_zcml())
    except NotImplementedError, e:
        # It appears that some other ftesting.zcml was already loaded, which
        # is perfectly fine -- the user might be running Zope 3 tests.
        if str(e) != 'Already configured with a different config file':
            raise
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    dir = os.path.dirname(__file__)
    filenames = [fn for fn in os.listdir(dir)
                 if fn.endswith('.txt') and not fn.startswith('.')]
    suites = [
        FunctionalDocFileSuite(filename,
                               globs={'analyze': analyze},
                               optionflags=optionflags)
              for filename in filenames]
    return unittest.TestSuite(suites)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
