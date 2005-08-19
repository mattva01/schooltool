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
Main SchoolBell script.

This module is not necessary if you use SchoolBell as a Zope 3 content object.
It is only used by the standalone SchoolBell executable.

$Id$
"""
import locale
import gettext
import os.path
from schooltool.app import main

locale_charset = locale.getpreferredencoding()

localedir = os.path.join(os.path.dirname(__file__), '..', 'locales')
catalog = gettext.translation('schooltool', localedir, fallback=True)
_ = lambda us: catalog.ugettext(us).encode(locale_charset, 'replace')

sb_incompatible_db_error_msg = _("""
This is not a SchoolBell 1.0 database file, aborting.
""").strip()


sb_old_db_error_msg = _("""
This is not a SchoolBell 1.0 database file, aborting.

Please run the standalone database upgrade script.
""").strip()


class Options(main.Options):
    """SchoolBell process options."""

    config_filename = 'schoolbell.conf'


class StandaloneServer(main.StandaloneServer):

    incompatible_db_error_msg = sb_incompatible_db_error_msg
    old_db_error_msg = sb_old_db_error_msg

    system_name = "SchoolBell"

    Options = Options


if __name__ == '__main__':
    StandaloneServer().main()
