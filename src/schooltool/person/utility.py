#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
from schooltool.person.person import Person
from schooltool.table.table import url_cell_formatter
from schooltool.table.table import IndexedLocaleAwareGetterColumn


class PersonFactoryUtility(object):

    def columns(self):
        title = IndexedLocaleAwareGetterColumn(
            index='title',
            name='title',
            title=u'Full Name',
            getter=lambda i, f: i.title,
            cell_formatter=url_cell_formatter,
            subsort=True)
        return [title]

    def sortOn(self):
        return (("title", False),)

    def __call__(self, *args, **kw):
        return Person(*args, **kw)

    def createManagerUser(self, username, system_name):
        result = self(username, "%s %s" % (system_name, "Manager"))
        return result
