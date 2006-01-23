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
"""Dashboard Implementation

$Id$
"""
__docformat__ = 'reStructuredText'
import zope.component
import zope.interface
from zope.viewlet import manager, viewlet

import schooltool.person
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.dashboard import interfaces


class Dashboard(manager.ViewletManagerBase):
    zope.interface.implements(interfaces.IDashboard)

    table = None

    def __getitem__(self, name):
        """See zope.interface.common.mapping.IReadMapping"""
        viewlet = super(Dashboard, self).__getitem__(name)
        if not viewlet.isAvailable():
            raise zope.component.interfaces.ComponentLookupError(
                'Viewlet `%s` is not available.' %name)

    def createTable(self):
        self.table = [[], []]
        for index in range(len(self.viewlets)):
            self.table[index%2].append(self.viewlets[index])

    def filter(self, viewlets):
        """Filter by by availability."""
        viewlets = super(Dashboard, self).filter(viewlets)
        return [(name, viewlet) for name, viewlet in viewlets
                if viewlet.isAvailable()]

    def sort(self, viewlets):
        """Sort the viewlets by weight."""
        return sorted(viewlets, key=lambda v: v[1].getWeight())

    def update(self):
        super(Dashboard, self).update()
        self.createTable()


class DashboardCategory(viewlet.ViewletBase):
    zope.interface.implements(interfaces.IDashboardCategory)

    groups = []
    weight = 100

    # See interfaces.IDashboardCategory
    title = ''

    def getWeight(self):
        """See interfaces.IDashboardCategory"""
        return int(self.weight)

    def isAvailable(self):
        """See interfaces.IDashboardCategory"""
        return True


class SectionsCategory(DashboardCategory):

    def getSections(self):
        person = schooltool.person.interfaces.IPerson(self.request.principal)
        for section in ISchoolToolApplication(None)['sections'].values():
            if person in section.members:
                yield section
