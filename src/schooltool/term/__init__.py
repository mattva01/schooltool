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
"""SchoolTool terms package

A term defines a range in time (e.g. September 1 to December 31, 2004) and for
every day within that range it defines whether that day is a schoolday or a
holiday.


$Id$
"""
from schooltool.app.app import InitBase


class TermInit(InitBase):

    def __call__(self):
        from schooltool.term.term import TermContainer
        self.app['terms'] = TermContainer()


def registerTestSetup():
    from schooltool.testing import registry

    def addTermContainer(app):
        from schooltool.term.term import TermContainer
        app['terms'] = TermContainer()

    registry.register('ApplicationContainers', addTermContainer)

registerTestSetup()
del registerTestSetup
