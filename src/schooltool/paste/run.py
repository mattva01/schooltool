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
SchoolTool run script that

$Id$
"""
import sys
import optparse
import os.path
import paste.script.command


def parse_args(argv):
    """Parse the command line arguments"""
    parser = optparse.OptionParser(usage="usage: %prog INSTANCE")
    options, args = parser.parse_args(argv)
    if len(args) != 2:
        parser.error("""Missing instance to start up! You can create one using make-scooltool-instance.""")
    return options, args


def main():
    options, args = parse_args(sys.argv)
    conf_file = os.path.join(os.path.abspath(args[1]), 'schooltool.ini')
    paste.script.command.run(['serve', conf_file])
