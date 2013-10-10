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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import os.path
import pkg_resources
from paste.script.templates import var, Template

HOME = os.path.expanduser('~')

def get_available_types():
    instance_types = list(pkg_resources.iter_entry_points('schooltool.instance_type'))
    return [(entry.name, entry.module_name) for entry in sorted(instance_types)]

available_types = get_available_types()


def get_paste_parts():
    paste_part_factories = list(pkg_resources.iter_entry_points(
            'schooltool.paste_configuration'))
    return [entry.load() for entry in paste_part_factories]

paste_configurers = get_paste_parts()


class SchoolToolDeploy(Template):
    _template_dir = 'schooltool_template'
    summary = "(Paste) deployment of a SchoolTool application"

    vars = [
        var('instance_type', """SchoolTool instance type to use. Available types -
  %s""" % "\n  ".join([t[0] for t in available_types]),
            default='schooltool')]

    def check_vars(self, vars, cmd):
        vars = super(SchoolToolDeploy, self).check_vars(vars, cmd)
        vars['instance_package'] = dict(available_types)[vars['instance_type']]
        vars['config_dir'] = os.path.join(
            os.path.abspath(cmd.options.output_dir), vars['project'])
        vars['bin_dir'] = os.path.abspath(
            vars.get('bin_dir', 'bin'))
        vars['log_dir'] = os.path.abspath(
            vars.get('log_dir', os.path.join(vars['project'], 'log')))
        vars['data_dir'] = os.path.abspath(
            vars.get('data_dir', os.path.join(vars['project'], 'var')))
        vars['run_dir'] = os.path.abspath(
            vars.get('run_dir', os.path.join(vars['project'], 'run')))
        vars['paste_extra_paths'] = ''
        vars['paste_extra_parts'] = ''
        for factory in paste_configurers:
            factory(vars)
        return vars

    def write_files(self, command, output_dir, vars):
        super(SchoolToolDeploy, self).write_files(command, output_dir, vars)
        for directory in (vars['log_dir'], vars['data_dir'], vars['run_dir']):
            if not os.path.exists(directory):
                print "Creating directory %s" % directory
                if not command.simulate:
                    os.makedirs(directory)
