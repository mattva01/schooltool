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
import os.path
import pkg_resources
from paste.script.templates import var, Template

HOME = os.path.expanduser('~')

def get_available_types():
    instance_types = list(pkg_resources.iter_entry_points('schooltool.instance_type'))
    return [entry.load().__name__ for entry in instance_types]

available_types = get_available_types()


class SchoolToolDeploy(Template):
    _template_dir = 'schooltool_template'
    summary = "(Paste) deployment of a SchoolTool application"

    vars = [
        var('instance_type', """SchoolTool instance type to use. Available types -
  %s""" % "\n  ".join(available_types), default=available_types[-1])]

    def check_vars(self, vars, cmd):
        vars = super(SchoolToolDeploy, self).check_vars(vars, cmd)
        vars['abspath'] = os.path.join(os.path.abspath(cmd.options.output_dir), vars['project'])
        return vars
