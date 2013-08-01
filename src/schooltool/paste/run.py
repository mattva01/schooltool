#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007, 2011 Shuttleworth Foundation
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
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
"""
SchoolTool run script.
"""

from __future__ import with_statement

import optparse
import os
import os.path

import paste.script.command


def parse_args():
    """Parse the command line arguments"""
    parser = optparse.OptionParser(usage="usage: %prog INSTANCE [options]")
    parser.add_option("--daemon",
                      action="store_true",
                      dest="start_daemon",
                      help="Run in daemon (background) mode")
    parser.add_option('--pid-file',
                      dest='pid_file',
                      metavar='FILENAME',
                      help="Save PID to file (if running in daemon mode)")
    parser.add_option('--log-file',
                      dest='log_file',
                      metavar='LOG_FILE',
                      help="Save output to the given log file (redirects stdout)")
    parser.add_option("--stop-daemon",
                      action="store_true",
                      dest="stop_daemon",
                      help="Stop a daemonized server")
    parser.add_option('--reload',
                      dest='reload',
                      action='store_true',
                      help="Use auto-restart file monitor")
    parser.add_option('--reload-interval',
                      dest='reload_interval',
                      default=1,
                      help="Seconds between checking files (low number can cause significant CPU usage)")
    parser.add_option('--monitor-restart',
                      dest='monitor_restart',
                      action='store_true',
                      help="Auto-restart server if it dies")
    parser.add_option("--status",
                      action="store_true",
                      dest="show_status",
                      help="Show the status of the (presumably daemonized) server")
    parser.add_option('--user',
                      dest='set_user',
                      metavar="USERNAME",
                      help="Set the user (usually only possible when run as root)")
    parser.add_option('--group',
                      dest='set_group',
                      metavar="GROUP",
                      help="Set the group (usually only possible when run as root)")
    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error("""Missing instance to start up! You can create one using make-scooltool-instance.""")

    instance_root = os.path.abspath(args[0])
    conf_file = os.path.join(instance_root, "paste.ini")
    if not os.path.exists(conf_file):
        parser.error("This is not a schooltool instance: %s" % args[0])
    args[0] = conf_file

    if (options.start_daemon or
        options.stop_daemon or
        options.show_status):
        if not options.pid_file:
            options.pid_file = os.path.join(instance_root,
                                            "var", "schooltool.pid")
        if not options.log_file:
            options.log_file = os.path.join(instance_root,
                                            "log", "paster.log")
    return options, args


def set_default_celery_config():
    if 'CELERY_CONFIG_MODULE' not in os.environ:
        os.environ['CELERY_CONFIG_MODULE']='schooltool.task.config.zope'


def main():
    options, args = parse_args()
    conf_file = os.path.abspath(args[0])

    set_default_celery_config()

    extra_options = []
    if options.start_daemon:
        extra_options.append('--daemon')
    if options.stop_daemon:
        extra_options.append('--stop-daemon')
    if options.reload:
        extra_options.append('--reload')
    if options.reload_interval:
        extra_options.append('--reload-interval=%s' % options.reload_interval)
    if options.monitor_restart:
        extra_options.append('--monitor-restart')
    if options.show_status:
        extra_options.append('--status')
    if options.set_user:
        extra_options.append('--user=%s' % options.set_user)
    if options.set_group:
        extra_options.append('--group=%s' % options.set_group)
    if (options.start_daemon or
        options.stop_daemon or
        options.show_status):
        extra_options.extend(['--pid-file=%s' % options.pid_file,
                              '--log-file=%s' % options.log_file])

    paste.script.command.run(['serve', conf_file] + extra_options)
