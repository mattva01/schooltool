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
Functional tests for devmode.

$Id: test_all.py 2922 2005-02-22 19:04:44Z mg $
"""

import os
import unittest

from zope.testing import doctest
from zope.app.testing.functional import FunctionalDocFileSuite

from schooltool.app.browser.ftests.test_all import find_ftesting_zcml
from zope.app.testing.functional import FunctionalTestSetup

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
    return unittest.TestSuite((
        FunctionalDocFileSuite('devmode.txt', optionflags=optionflags),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
