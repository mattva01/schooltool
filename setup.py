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
from distutils.archive_util import ARCHIVE_FORMATS
from distutils.dir_util import mkpath
from distutils.spawn import spawn


#
# Distutils Customization
#

def make_schooltool_tarball(base_name, base_dir, verbose=0, dry_run=0):
    """Make a tarball with the right permissions/owenership."""
    archive_name = base_name + ".tar"
    mkpath(os.path.dirname(archive_name), dry_run=dry_run)
    spawn(["tar", "--owner=0", "--group=0", "--mode=a+r",
           "-cf", archive_name, base_dir], dry_run=dry_run)
    spawn(["gzip", "-f9", archive_name], dry_run=dry_run)
    return archive_name + '.gz'

# Register custom archive creation function
ARCHIVE_FORMATS['schooltooltgz'] = (make_schooltool_tarball, [],
                                    "create tarball with schooltool defaults")

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
            ('default-config=', None, "location of the default server config"
                    " file")]

    def initialize_options(self):
        self.paths = None
        self.default_config = None
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
# if you modify this, also modify MANIFEST.in recursive includes
datafile_re = re.compile('.*\.(pt|js|png|gif|css|mo|rng|xml|zcml|pot|po)\Z')
data_files = []
for root, dirs, files in os.walk(os.path.join('src', 'schooltool')):
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

# Setup SchoolTool
setup(name="schooltool",
    description="A common information systems platform for school administration.",
    long_description="""
SchoolTool is an open source school management information system.  It is
a distributed client/server system.  The SchoolTool server presents two
interfaces to clients:

  - a traditional web application interface, usable with an ordinary browser.

  - HTTP-based programming interface suitable for fat clients, adhering to
    the Representational State Transfer (REST) architectural style (see
    http://rest.blueoxen.net/).

The web application interface is the primary one.  The RESTive interface is
there for potential interoperability with other systems and fat clients to
perform data entry that is inconvenient to do via the web application
interface.

There are several clients that demonstrate the usage of the REST interface
(a command-line client that is used for functional tests, a wxWidgets GUI
client, and a command-line client for data import).

Any modern web browser is suitable for the web application interface.  The
interface degrades gracefully, so a browser that does not support CSS or
Javascript will be usable, although perhaps not very nice or convenient.
    """,
    version="0.10pre1",
    url='http://www.schooltool.org',
    license="GPL",
    maintainer="SchoolTool development team",
    maintainer_email="schooltool-dev@schooltool.org",
    platforms=["any"],
    classifiers=["Development Status :: 5 - Production/Stable",
    "Environment :: Web Environment",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: GNU General Public License (GPL)",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Zope",
    "Topic :: Education",
    "Topic :: Office/Business :: Scheduling"],
    cmdclass={'install': install,
        'install_scripts': install_scripts,
        'install_data': install_data},
    package_dir={'': 'src'},
    packages=['schooltool', 'schooltool.rest', 'schooltool.browser'],
    data_files=data_files + [('', ['schooltool.conf.in'])],
    scripts=['scripts/schooltool', 'scripts/schooltool-rest-client']
    )
