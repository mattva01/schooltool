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
SchoolBell setup script.
"""

# TODO - allow for separate installation of iCal parser

# Check python version
import sys
if sys.version_info < (2, 3):
    print >> sys.stderr, '%s: need Python 2.3 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)

import os
import re
from distutils.core import setup
from distutils.command.install import install as _install
from distutils.command.install_data import install_data as _install_data
from distutils.command.install_scripts \
        import install_scripts as _install_scripts

#
# Distutils Customization
#

class install_data(_install_data):
    """Specialized Python installer for SchoolBell.

    This install data command changes the default SchoolBell data install
    directory to be the same as the directory for install_lib, this should
    dissapear when python 2.4 is available more widely and package_data is
    available.

    It also makes the --install-data option to the install command a no-op.

    IMPORTANT: things will break if --install-dir is passed directly to an
    install_data command and the --install-dir is not where install_lib put/will
    put the libraries.
    """

    def finalize_options(self):
        self.set_undefined_options('install',
                ('install_lib', 'install_dir'))
        return _install_data.finalize_options(self)


class install(_install):
    """Specialized install command for schoolbell.

    Make it possilble to pass the --paths and --default-config options to the
    install_scripts command.
    """

    user_options = _install.user_options + [
            ('paths=', None, "a semi-colon separated list of paths that should"
                " be added to the python path on script startup"),
            ('default-config=', None, "location of the default server config"
                    " file")]

    def initialize_options(self):
        self.paths = None
        self.default_config = None
        return _install.initialize_options(self)


class install_scripts(_install_scripts):
    """Specialized Python installer for SchoolBell.

    The primary purpose of this sub class it to customize the scripts on
    installation. By setting their default path and config file.

    By default, no extra paths are added and the default config file is set to
    be a file in the same directory as the script with a .conf extension.
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
        if not self.paths:
            self.paths = ''
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
            paths_regex = re.compile(r'# paths begin\n.*# paths end', re.S)
            paths = ['# paths begin', '# paths end']
            for path in self.paths.split(';'):
                paths.insert(-1, 'sys.path.insert(0, %s)' \
                        % repr(os.path.abspath(path)))
            script_str = re.sub(paths_regex, '\n'.join(paths), script_str)
            # Update the default config file
            config_regex = re.compile(r'# config begin\n.*# config end', re.S)
            config = ['# config begin',
                    'sys.argv.insert(1, \'--config=%s.conf\' % __file__)',
                    '# config end']
            if self.default_config:
                config[1] = 'sys.argv.insert(1, \'--config=%s\')'\
                        % os.path.abspath(self.default_config)
            script_str = re.sub(config_regex, '\n'.join(config), script_str)
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

# Patch the setup command so that python 2.3 distutils can deal with the
# classifiers option
if sys.version_info < (2, 3):
    _setup = setup
    def setup(**kwargs):
        if kwargs.has_key("classifiers"):
            del kwargs["classifiers"]
        _setup(**kwargs)

# find the data files
# this regex should be similar to the MANIFEST.in recursive includes
datafile_re = re.compile('.*\.(pt|js|png|gif|css|mo|rng|xml|zcml)\Z')
data_files = []
for root, dirs, files in os.walk(os.path.join('src', 'schoolbell')):
    # Ignore testing directories
    if 'ftests' in dirs:
        dirs.remove('ftests')
    if 'tests' in dirs:
        dirs.remove('tests')
    # Find the data files
    tmp = [os.path.join(root, file) for file in files \
            if datafile_re.match(file, 1)]
    # If any, add them to the files to be copied
    if tmp:
        data_files.append((root[4:], tmp))

# Final setup of SchoolBell
setup(name="schoolbell",
    description="A standalone or Zope 3 component calendaring server",
    long_description="""A calendaring server which can be used as a
        standalone server or a Zope 3 component. This server allows for
        people and resources to have individual and group calendars.
        The calendars are:
        * Shareable
        * Overlayable
        * Access controllable
        * Importable and exportable to iCal clients
            (e.g. Apple's iCal or Mozilla Sunbird)

        And will:
        * Time zone aware
        * Provide resource rooking
        * Do anything else that makes sense

        All of this is accessible through a web interface which is simple,
        powerful and beautiful.

        For developers SchoolBell offers:
        * Re-usable calendaring Zope 3 components.
        * iCal parser.
        * Rigourous functional and unit testing.

        Enjoy!""",
    version="1.1rc1",
    url='http://www.schooltool.org/schoolbell',
    license="GPL",
    maintainer="SchoolTool development team",
    maintainer_email="schooltool-dev@schooltool.org",
    platforms=["any"],
    classifiers=["Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: GNU General Public License (GPL)",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Zope",
#        "Topic :: Office/Business :: Groupware", TODO are we groupware?
    "Topic :: Office/Business :: Scheduling"],
    cmdclass={'install': install,
        'install_data': install_data,
        'install_scripts': install_scripts},
    package_dir={'': 'src'},
    packages=['schoolbell',
        'schoolbell.relationship',
        'schoolbell.calendar',
        'schoolbell.app',
        'schoolbell.app.browser',
        'schoolbell.app.rest',
        'schoolbell.app.generations'],
    data_files=data_files,
    scripts=['scripts/schoolbell'])
