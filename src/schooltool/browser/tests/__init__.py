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
from schooltool.tests.utils import RegistriesSetupMixin


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
        if context is not None:
            self.assert_(destination.context is context)
        return destination


class AppSetupMixin(RegistriesSetupMixin):

    def setUpSampleApp(self):
        from schooltool.model import Group, Person, Resource
        from schooltool.app import Application, ApplicationObjectContainer
        from schooltool.membership import Membership
        from schooltool import membership
        self.setUpRegistries()
        membership.setUp()
        self.app = app = Application()
        app['groups'] = ApplicationObjectContainer(Group)
        app['persons'] = ApplicationObjectContainer(Person)
        app['resources'] = ApplicationObjectContainer(Resource)
        self.root = app['groups'].new("root", title="root")
        self.locations = app['groups'].new("locations", title="locations")
        self.managers = app['groups'].new("managers", title="managers")
        self.teachers = app['groups'].new("teachers", title="teachers")
        self.person = app['persons'].new("johndoe", title="John Doe")
        self.person2 = app['persons'].new("notjohn", title="Not John Doe")
        self.manager = app['persons'].new("manager", title="Manager")
        self.teacher = app['persons'].new("teacher", title="Prof. Bar")
        self.resource = app['resources'].new("resource", title="Kitchen sink")
        self.location = app['resources'].new("location", title="Inside")
        self.location2 = app['resources'].new("location2", title="Outside")

        Membership(group=self.root, member=self.person)
        Membership(group=self.managers, member=self.manager)
        Membership(group=self.teachers, member=self.teacher)
        Membership(group=self.locations, member=self.location)
        Membership(group=self.locations, member=self.location2)

    setUp = setUpSampleApp

    # tearDown is inherited from the RegistriesSetupMixin.

