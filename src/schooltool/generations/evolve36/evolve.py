#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 36.
"""

from schooltool.testing.mock import ModulesSnapshot
from schooltool.generations.evolve36.helper import BuildContext
from schooltool.generations.evolve36.timetable_builders import \
    SchoolTimetablesBuilder


# XXX: This holds references to substitute classes
#      so that they can be pickled afterwards.
from schooltool.generations.evolve36 import model

def evolveTimetables(app):
    modules = ModulesSnapshot()

    modules.mock_module('schooltool.timetable')
    modules.mock(model.substitutes)

    builders = [
        SchoolTimetablesBuilder(),
        ]

    for builder in builders:
        builder.read(app)

    modules.restore()

    for builder in builders:
        builder.clean(app)

    for builder in builders:
        builder.build(BuildContext(app=app))

