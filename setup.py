#!/usr/bin/env python2.3
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005    Shuttleworth Foundation,
#                       Brian Sutherland
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
SchoolTool setup script.
"""

#
# Check requisite version numbers
#

import sys
import os
import re

# Check python version
if sys.version_info < (2, 3):
    print >> sys.stderr, '%s: need Python 2.3 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)

# Subclass some distutils commands so that we can set up the server on install
from distutils.command.install import install as _install
from distutils.command.install_data import install_data as _install_data
from distutils.command.install_scripts import \
        install_scripts as _install_scripts


class install_data(_install_data):
    """Specialized Python installer for schooltool.

    It changes the default schoolbell data install directory to be the same as
    the directory for install_lib.

    It also makes the --install-data option to the install command a no-op.

    The right way to go about this is package_data, but that is only in
    python 2.4.
    """

    def finalize_options(self):
        self.set_undefined_options('install',
                ('install_lib', 'install_dir'))
        return _install_data.finalize_options(self)


class install(_install):
    """Specialized install command for schooltool and schoolbell.

    Make it possilble to pass the --paths and --default-config options to the
    install_scripts command.
    """

    user_options = _install.user_options + [
            ('paths=', None, "a semi-colon separated list of paths that should"
                " be added to the python path on script startup"),
            ('datafile-dir=', None, "override where the python libraries think"
                    " their data files are"),
            ('default-config=', None, "location of the default server config"
                    " file")]

    def initialize_options(self):
        self.paths = None
        self.default_config = None
        self.datafile_dir = None
        return _install.initialize_options(self)


class install_scripts(_install_scripts):
    """Specialized Python installer for schooltool and schoolbell.

    The primary purpose of this sub class it to configure the scripts on
    installation.
    """

    user_options = _install_scripts.user_options + [
            ('paths=', None, "a semi-colon separated list of paths that should"
                " be added to the python path on script startup"),
            ('default-config=', None, "location of the default server config"
                    " file")]

    def initialize_options(self):
        self.paths = None
        self.default_config = None
        return _install_scripts.initialize_options(self)

    def finalize_options(self):
        self.set_undefined_options('install',
                ('paths', 'paths'),
                ('default_config', 'default_config'))
        return _install_scripts.finalize_options(self)

    def update_scripts(self):
        for script in self.get_outputs():
            # Read the installed script
            try:
                script_file = open(script, 'r')
                script_str = script_file.read()
            finally:
                script_file.close()
            # Update the paths in the script
            if self.paths:
                paths_str = '\n'.join(['# paths begin']
                        + ['sys.path.insert(0, %s)' % repr(path)\
                        for path in self.paths.split(';')] + ['# paths end'])
            else:
                paths_str = '\n'.join(['# paths begin', '# paths end'])
            paths_regex = re.compile(r'# paths begin\n.*# paths end', re.S)
            script_str = re.sub(paths_regex, paths_str, script_str)
            # Update the default config file
            if self.default_config:
                config_str = '\n'.join(['# config begin',
                        'sys.argv.insert(1, \'--config=%s\')'
                        % self.default_config, '# config end'])
            else:
                config_str = '\n'.join(['# config begin',
                        "sys.argv.insert(1, \'--config=%s\' % "
                        "__file__ + \'.conf\')",
                        '# config end'])
            config_regex = re.compile(r'# config begin\n.*# config end', re.S)
            script_str = re.sub(config_regex, config_str, script_str)
            # Write the script again
            try:
                script_file = open(script, 'w')
                script_file.write(script_str)
            finally:
                script_file.close()

    def run(self):
        ans = _install_scripts.run(self)
        self.update_scripts()
        return ans


#
# Do the setup
#

from distutils.core import setup

# Patch the setup command so that python 2.3 distutils can deal with the
# classifiers option
if sys.version_info < (2, 3):
    _setup = setup
    def setup(**kwargs):
        if kwargs.has_key("classifiers"):
            del kwargs["classifiers"]
        _setup(**kwargs)

# regex for finding data files
datafile_re = re.compile('.*\.(pt|js|png|css|mo|rng|xml|pot|zcml)\Z')

# TODO: ask distutils to build Zope 3 extension modules somehow
# find the data files
data_files = []
os.chdir('src')
for root, dirs, files in os.walk('schooltool'):
    tmp = [os.path.join('src', root, file) for file in files \
            if datafile_re.match(file, 1)]
    if tmp:
        data_files.append((root, tmp))
os.chdir('..')

# Setup SchoolTool
setup(name="schooltool",
    version="0.10rc1",
    url='http://www.schooltool.org',
    cmdclass={'install': install,
        'install_scripts': install_scripts,
        'install_data': install_data},
    package_dir={'': 'src'},
    packages=['schooltool'],
    ## XXX - these comments represent features from the twisted schooltool,
    ## which may still appear in the new schooltool, so keep them around for
    ## reference
    #    'schooltool.interfaces',
    #    'schooltool.schema', 'schooltool.translation',
    #    'schooltool.rest', 'schooltool.browser',
    #    'schooltool.clients'],
    #data_files=[('sampleschool', ['persons.csv', 'groups.csv',
    #        'resources.csv', 'timetable.csv', 'ttconfig.data'])]
    #    + data_files + [('', ['schooltool.conf.in'])],
    #scripts=['scripts/import-sampleschool', 'scripts/schooltool',
    #    'scripts/schooltool-client']
    scripts=['scripts/schooltool']
    )
