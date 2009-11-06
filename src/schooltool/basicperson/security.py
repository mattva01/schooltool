#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
Lyceum specific security code.

$Id$

"""
from schooltool.basicperson.interfaces import IBasicPerson
from schooltool.group.interfaces import IGroupContainer
from schooltool.securitypolicy.crowds import ConfigurableCrowd
from schooltool.app.interfaces import ISchoolToolApplication


class PersonInfoViewersCrowd(ConfigurableCrowd):
    """The crowd of people who can view the info of a person."""

    setting_key = 'everyone_can_view_person_info'

    def contains(self, principal):
        container = IGroupContainer(ISchoolToolApplication(None), None)
        if container is None or 'teachers' not in container:
            return False
        teachers = container['teachers']
        groups = list(IBasicPerson(self.context).groups)
        return (ConfigurableCrowd.contains(self, principal) or
                teachers in groups)

