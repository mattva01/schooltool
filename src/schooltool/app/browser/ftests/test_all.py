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
Functional tests for schooltool.app.app.
"""

import unittest

from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.browser import BrowserView

from schooltool.app.testing import app_functional_layer
from schooltool.testing.functional import collect_ftests


class BrokenView(BrowserView):
    implements(IBrowserPublisher)

    def browserDefault(self, request):
        return self, ()

    def publishTraverse(self, name, request):
        raise LookupError(name)

    def __call__(self):
        raise RuntimeError("Houston, we've got a problem")


def test_suite():
    return collect_ftests(layer=app_functional_layer)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
