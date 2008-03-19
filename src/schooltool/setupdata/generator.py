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
SchoolTool pluggable setup data generator

Setup data is created by a variety of plugins
that can state their dependencies on other plugins explicitly.
Dependencies must be acyclic.

Setup data generation plugins are named local utilities with an
interface schooltool.setupdata.interfaces.ISetupDataGeneratorPlugin.

$Id: generator.py 5224 2005-10-12 17:38:34Z alga $
"""
import time
from zope.component import getUtilitiesFor
from schooltool.setupdata.interfaces import ISetupDataPlugin
from schooltool.setupdata.interfaces import CyclicDependencyError


def generate(app):
    """Generate setup data provided by all plugins.

    Runs the generate functions of all plugins in an order such that
    the dependencies are all generated before the dependents.

    In essence, this function performs a topological sort in a
    directed acyclic graph.

    Raises a CyclicDependencyError if the dependency graph has a cycle.

    Returns a dict with names of plugins run as keys and CPU times as
    values.
    """

    plugins = dict([(obj.name, obj) for name, obj in
                    getUtilitiesFor(ISetupDataPlugin)])


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

    # dict with used CPU cycles for each plugin
    times = {}

    def visit(name):
        """The recursive part of the topological sort

        Raises a CyclicDependencyError if cyclic depencencies are found.
        """
        if status[name] == new:
            status[name] = open
            plugin = plugins[name]
            for dep in plugin.dependencies:
                visit(dep)
            start = time.clock()
            plugin.generate(app)
            times[name] = time.clock() - start
            status[name] = closed
        elif status[name] == closed:
            return
        elif status[name] == open:
            raise CyclicDependencyError("cyclic dependency at '%s'" % name)

    for name in plugins:
        visit(name)

    return times
