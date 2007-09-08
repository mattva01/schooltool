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


def parse_args():
    """Parse the command line arguments"""
    parser = optparse.OptionParser(usage="usage: %prog INSTANCE [options]")
    parser.add_option("--daemon",
                      action="store_true",
                      dest="start_daemon",
                      help="Run in daemon (background) mode")
    parser.add_option("--stop-daemon",
                      action="store_true",
                      dest="stop_daemon",
                      help="Stop a daemonized server")
    parser.add_option("--status",
                      action="store_true",
                      dest="show_status",
                      help="Show the status of the (presumably daemonized) server")
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error("""Missing instance to start up! You can create one using make-scooltool-instance.""")
    return options, args


def main():
    options, args = parse_args()
    instance_root = os.path.abspath(args[0])
    conf_file = os.path.join(instance_root, "schooltool.ini")
    pid_file = os.path.join(instance_root, "var", "schooltool.pid")
    log_file = os.path.join(instance_root, "log", "paster.log")

    extra_options = []
    if options.start_daemon:
        extra_options.append('--daemon')
    if options.stop_daemon:
        extra_options.append('--stop-daemon')
    if options.show_status:
        extra_options.append('--status')
    if (options.start_daemon or
        options.stop_daemon or
        options.show_status):
        extra_options.extend(['--pid-file=%s' % pid_file,
                              '--log-file=%s' % log_file])

    paste.script.command.run(['serve', conf_file] + extra_options)
