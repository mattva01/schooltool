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

if sys.version_info < (2, 3):
    print >> sys.stderr, '%s: need Python 2.3 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)

try:
    import twisted.copyright
except ImportError:
    print >> sys.stderr, ("%s: apparently you do not have Twisted installed."
                          % sys.argv[0])
    print >> sys.stderr, "You will not be able to run the SchoolTool server."
    print >> sys.stderr
else:
    m = re.match(r"(\d+)[.](\d+)[.](\d+)(?:[a-z]+\d*)?$",
                 twisted.copyright.version)
    if not m:
        print >> sys.stderr, ("%s: you have Twisted version %s."
                              % (sys.argv[0], twisted.copyright.version))
        print >> sys.stderr, ("I was unable to parse the version number."
                              "  You will not be able to run")
        print >> sys.stderr, ("the SchoolTool server if this version is"
                              " older than 1.3.0.")
        print >> sys.stderr
    else:
        ver = tuple(map(int, m.groups()))
        if ver < (1, 3, 0):
            print >> sys.stderr, ("%s: you have Twisted version %s."
                                  % (sys.argv[0], twisted.copyright.version))
            print >> sys.stderr, ("You need at least version 1.3.0 in order to"
                                  " be able to run the SchoolTool")
            print >> sys.stderr, "server."
            print >> sys.stderr


# which package are we setting up
if sys.argv[1] == 'schooltool':
    package = 'schooltool'
    sys.argv[1:2] = []
elif sys.argv[1] == 'schoolbell':
    package = 'schoolbell'
    sys.argv[1:2] = []
else:
    print >> sys.stderr, ("You must specify the package to build as the first"
                        " command line option, either schooltool or schoolbell")
    sys.exit(1)

# Subclass some distutils commands so that we can set up the server on install

from distutils.command.install import install as _install
from distutils.command.install_lib import install_lib as _install_lib
from distutils.command.install_scripts import \
        install_scripts as _install_scripts


#### Begin Dirty hack
from distutils.command.install_data import install_data as _install_data
class install_data(_install_data):
    """Specialized Python installer for schoolbell.

    This install data command is for schoolbell only, it changes the default
    schoolbell data install directory to be the same as the directory for
    install_lib.

    It also makes the --install-data option to the install command a no-op.
    """

    def finalize_options(self):
        self.set_undefined_options('install',
                ('install_lib', 'install_dir'))
        return _install_data.finalize_options(self)
#### End dirty hack


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


class install_lib(_install_lib):
    """Specialized Python installer for schooltool and schoolbell.

    The primary purpose of this sub class it to make sure SchoolTool will
    know where it's data files are on installation.
    """

    package = package

    user_options = _install_lib.user_options + [
            ('datafile-dir=', None, "override where the python libraries think"
                    " their data files are")]

    def initialize_options(self):
        self.datafile_dir = None
        self.build_lib = None
        return _install_lib.initialize_options(self)

    def finalize_options(self):
        self.set_undefined_options('install',
                ('datafile_dir', 'datafile_dir'),
                ('build_lib', 'build_lib'))
        # datafile_dir not set in install, get it from install_data
        self.set_undefined_options('install_data',
                ('install_dir', 'datafile_dir'))
        return _install_lib.finalize_options(self)

    def update_pathconfig(self):
        # Write the new location to the pathconfig.py file.
        pathconfig = os.path.join(self.build_lib, self.package, 'pathconfig.py')
        ##### Begin dirty hack
        # schoolbell does not support installing data files and modules
        # separately so this hack prevents people from doing so
        if self.package == 'schoolbell':
            if os.path.abspath(self.datafile_dir) \
                    != os.path.abspath(self.install_dir):
                print >> sys.stderr, ("WARNING: You are probably trying to "
                        "install schoolbell data files and modules in "
                        "different locations, this is not implemented and "
                        "probably won't work.")
        ##### End dirty hack
        try:
            path_file = open(pathconfig, 'r')
            pathconfig_str = path_file.read()
        finally:
            path_file.close()
        # Update the pathconfig string file
        path_to_data = os.path.abspath(
                os.path.join(self.datafile_dir, self.package))
        datafile_str = '\n'.join(['# pathconf begin', 'DATADIR = %s'
                % repr(path_to_data),
                '# pathconf end'])
        datafile_regex = re.compile(r'# pathconf begin\n.*# pathconf end', re.S)
        pathconfig_str = re.sub(datafile_regex, datafile_str, pathconfig_str)
        try:
            path_file = open(pathconfig, 'w')
            path_file.write(pathconfig_str)
        finally:
            path_file.close()

    def run(self):
        self.build()
        self.update_pathconfig()
        outfiles = self.install()
        if outfiles is not None and self.distribution.has_pure_modules():
            self.byte_compile(outfiles)


class install_scripts(_install_scripts):
    """Specialized Python installer for schooltool and schoolbell.

    The primary purpose of this sub class it to configure the scripts on
    installation.
    """

    package = package

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

# Set a default manifest
if sys.argv[1] == 'sdist':
    sys.argv[2:2] = ['-t', 'MANIFEST.in.' + package,
            '-m', 'MANIFEST.' + package]

# regex for finding data files
datafile_re = re.compile('.*\.(pt|js|png|css|mo|rng|xml|pot|zcml)\Z')

# TODO: ask distutils to build Zope 3 extension modules somehow
if package == 'schooltool':
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
            'install_lib': install_lib},
        package_dir={'': 'src'},
        packages=['schooltool', 'schooltool.interfaces',
            'schooltool.schema', 'schooltool.translation',
            'schooltool.rest', 'schooltool.browser',
            'schooltool.clients'],
        data_files=[('sampleschool', ['persons.csv', 'groups.csv',
                'resources.csv', 'timetable.csv', 'ttconfig.data'])]
            + data_files + [('', ['schooltool.conf.in'])],
        scripts=['scripts/import-sampleschool', 'scripts/schooltool',
            'scripts/schooltool-client'])
elif package == 'schoolbell':
    # find the data files
    data_files = []
    os.chdir('src')
    for root, dirs, files in os.walk('schoolbell'):
        tmp = [os.path.join('src', root, file) for file in files \
                if datafile_re.match(file, 1)]
        if tmp:
            data_files.append((root, tmp))
    os.chdir('..')
    # Setup SchoolBell
    setup(name="schoolbell",
        version="1.0rc1",
        url='http://www.schooltool.org/schoolbell',
        cmdclass={'install': install,
            'install_data': install_data,
            'install_scripts': install_scripts,
            'install_lib': install_lib},
        package_dir={'': 'src'},
        packages=['schoolbell', 'schoolbell.relationship',
            'schoolbell.calendar', 'schoolbell.app', 'schoolbell.app.browser'],
        data_files=data_files + [('', ['schoolbell.conf.in'])],
        scripts=['scripts/schoolbell'])
