#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Unit tests for the schooltool.browser package.
"""

from schooltool.rest.tests import RequestStub, setPath     # reexport


class TraversalTestMixin:

    def assertTraverses(self, view, name, viewclass, context=None,
                        request=None):
        """Assert that traversal returns the appropriate view.

        Checks that view._traverse(name, request) returns an instance of
        viewclass, and that the context attribute of the new view is
        identical to context.
        """
        if request is None:
            request = RequestStub()
        destination = view._traverse(name, request)
        self.assert_(isinstance(destination, viewclass))
        self.assert_(destination.context is context)
        return destination
