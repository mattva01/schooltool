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
Creating SchoolTool Instances

$Id$
"""
import os
import sys

import zope
from zope.app.server.mkzopeinstance import parse_args, Application

import schooltool

class SchoolToolApplication(Application):

    def copy_skeleton(self):
        options = self.options
        # TODO we should be able to compute the script
        script = os.path.abspath(sys.argv[0])
        zope_home = os.path.dirname(os.path.dirname(script))
        zope_init = os.path.abspath(zope.__file__)
        zope_software_home = os.path.dirname(os.path.dirname(zope_init))
        st_init = os.path.abspath(schooltool.__file__)
        st_software_home = os.path.dirname(os.path.dirname(st_init))
        self.replacements = [
            ("<<USERNAME>>",                 options.username),
            ("<<PASSWORD>>",                 options.password),
            ("<<PYTHON>>",                   sys.executable),
            ("<<INSTANCE_HOME>>",            options.destination),
            ("<<ZOPE_HOME>>",                zope_home),
            ("<<ZOPE_SOFTWARE_HOME>>",       zope_software_home),
            ("<<SCHOOLTOOL_SOFTWARE_HOME>>", st_software_home),
            ]
        self.copytree(self.options.skeleton, self.options.destination)


def main(argv=None, from_checkout=False):
    """Top-level script function to create a new SchoolTool instance."""
    if argv is None:
        argv = sys.argv
    try:
        options = parse_args(argv, from_checkout)
    except SystemExit, e:
        if e.code:
            return 2
        else:
            return 0
    app = SchoolToolApplication(options)
    try:
        return app.process()
    except KeyboardInterrupt:
        return 1
    except SystemExit, e:
        return e.code
