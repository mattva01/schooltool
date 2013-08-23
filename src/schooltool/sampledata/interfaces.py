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
SchoolTool sample data generator interfaces
"""
import zope.interface
import zope.schema


class ISampleDataPlugin(zope.interface.Interface):
    """A plugin that generates some sample data.

    These plugins may depend on other sample data plugins.  Say,
    calendar event generators depend on person generators.  All
    plugins have unique names and other plugins reference their
    dependencies by these names.
    """

    name = zope.schema.Id(title=u"Sample data generator name")

    dependencies = zope.schema.List(
        title=u"A list of dependenies",
        value_type=zope.schema.Id(title=u"Sample data generator name"),
        description=u"""
        A list of names of sample data generators this one depends on.
        """)

    def generate(app, seed=None):
        """Generate sample data of this plugin.

        This method assumes the sample data this plugin depends on has
        been created.
        """


class CyclicDependencyError(ValueError):
    """Cyclic dependency of sample data plugins"""
