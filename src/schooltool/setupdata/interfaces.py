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
SchoolTool setup data generator interfaces

$Id: interfaces.py 5231 2005-10-12 19:45:06Z alga $
"""
import zope.interface
import zope.schema


class ISetupDataPlugin(zope.interface.Interface):
    """A plugin that generates some setup data.

    These plugins may depend on other setup data plugins.  Say,
    calendar event generators depend on person generators.  All
    plugins have unique names and other plugins reference their
    dependencies by these names.
    """

    name = zope.schema.Id(title=u"Setup data generator name")

    dependencies = zope.schema.List(
        title=u"A list of dependenies",
        value_type=zope.schema.Id(title=u"Setup data generator name"),
        description=u"""
        A list of names of setup data generators this one depends on.
        """)

    def generate(app, seed=None):
        """Generate setup data of this plugin.

        This method assumes the setup data this plugin depends on has
        been created.
        """


class CyclicDependencyError(ValueError):
    """Cyclic dependency of setup data plugins"""
