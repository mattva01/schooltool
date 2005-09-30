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
SchoolTool pluggable sample data generator

In order to be able to test SchoolTool with data sets comparable in
size to those used in real life routinely, we have this sample data
generation system.  Sample data is created by a variety of plugins
that can state their dependencies on other plugins explicitly.
Extension writers can provide plugins for sample data for their
extensions, building upon the data constructed by the plugins provided
with schooltool.  Dependencies must be acyclic.

Sample data generation plugins are named local utilities with an
interface schooltool.sampledata.interfaces.ISampleDataGeneratorPlugin.

$Id$
"""
from zope.app import zapi
from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.sampledata.interfaces import CyclicDependencyError

def generate(app, seed=None):
    """Generate sample data provided by all plugins.

    Runs the generate functions of all plugins in an order such that
    the dependencies are all generated before the dependents.

    In essence, this function performs a topological sort in a
    directed acyclic graph.

    Raises a ValueError if the dependency graph has a cycle.
    """
    plugins = dict([(obj.name, obj) for name, obj in
                    zapi.getUtilitiesFor(ISampleDataPlugin)])


    # status is a dict plugin names as keys and statuses as values.
    # Statuses can be as follows:
    #
    #   new    -- not yet visited
    #   closed -- already processed
    #   open   -- being processed
    #
    # Stumbling over an 'open' node means there is a cyclic dependency

    new = 'new'
    open = 'open'
    closed = 'closed'
    status = dict([(name, new) for name in plugins])

    def visit(name):
        """The recursive part of the topological sort

        Raises a ValueError if cyclic depencencies are found.
        """
        if status[name] == new:
            status[name] = open
            plugin = plugins[name]
            for dep in plugin.dependencies:
                visit(dep)
            plugin.generate(app, seed)
            status[name] = closed

        elif status[name] == closed:
            return

        elif status[name] == open:
            raise CyclicDependencyError("cyclic dependency at '%s'" % name)


    for name in plugins:
        visit(name)
