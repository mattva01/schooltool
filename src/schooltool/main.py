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
Main SchoolTool script.

This module is not necessary if you use SchoolTool as a Zope 3 content object.
It is only used by the standalone SchoolTool executable.

$Id$
"""

from schoolbell.app.main import StandaloneServer as SchoolBellServer
from schoolbell.app.main import Options as SchoolBellOptions


st_incompatible_db_error_msg = """
This is not a SchoolTool 0.10 database file, aborting.
""".strip()


st_old_db_error_msg = """
This is not a SchoolTool 0.10 database file, aborting.

Please run the standalone database upgrade script.
""".strip()


class Options(SchoolBellOptions):
    config_filename = 'schooltool.conf'


class StandaloneServer(SchoolBellServer):

    incompatible_db_error_msg = st_incompatible_db_error_msg
    old_db_error_msg = st_old_db_error_msg
    Options = Options
    system_name = 'SchoolTool'


if __name__ == '__main__':
    StandaloneServer().main()
