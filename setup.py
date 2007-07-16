#!/usr/bin/env python
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
import os

here = os.path.dirname(__file__)

# Check python version
import sys
if sys.version_info < (2, 4):
    print >> sys.stderr, '%s: need Python 2.4 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)

import site
site.addsitedir(os.path.join(here, 'eggs'))

import pkg_resources
pkg_resources.require("setuptools>=0.6a11")

from setuptools import setup, find_packages

def get_version():
    version_file = os.path.join(here, 'src', 'schooltool', 'version.txt')
    f = open(version_file, 'r')
    result = f.read()
    f.close()
    return result

# allowed extensions
ALLOWED_EXTENSIONS = ['conf','css', 'gif', 'ico', 'ics', 'js', 'mo', 'po', 'pt',
                      'png', 'txt', 'xml', 'xpdl', 'zcml']

# Define packages we want to recursively include, we do this explicitly here
# to avoid automatic accidents
root_packages = ['schooltool.app',
                 'schooltool.attendance',
                 'schooltool.calendar',
                 'schooltool.course',
                 'schooltool.dashboard',
                 'schooltool.devmode',
                 'schooltool.demographics',
                 'schooltool.generations',
                 'schooltool.group',
                 'schooltool.help',
                 'schooltool.locales',
                 'schooltool.person',
                 'schooltool.resource',
                 'schooltool.relationship',
                 'schooltool.securitypolicy',
                 'schooltool.setupdata',
                 'schooltool.skin',
                 'schooltool.table',
                 'schooltool.term',
                 'schooltool.tests',
                 'schooltool.testing',
                 'schooltool.timetable',
                 'schooltool.traverser',
                 'schooltool.utility',
                 'schooltool.widget',

                 # The schooltool configurations we maintain
                 'schooltool.stapp2005',
                 'schooltool.stapp2007',

                 # only needed for tests
                 'schooltool.sampledata',
                 'schooltool.gradebook',
                 'schooltool.requirement',
                 'schooltool.level',
                 ]

# Packages we want to non-recursively include
package_data = {'schooltool': ['*.zcml', 'version.txt']}

# filter packages eliminating things that don't match
# XXX - the next for loop is pretty insane and inefficient. Feel free to fix it
# all it does is find the files in each package that need to be included.
all_packages = set(find_packages('src'))
for package in all_packages:
    for root_package in root_packages:
        if package.startswith(root_package):
            package_data[package] = []
            includes = []
            package_dir = os.path.join(here, 'src', *package.split('.'))
            for root, dirs, files in os.walk(package_dir):
                if dir in set(dirs):
                    if dir.startswith('.'):
                        dirs.remove(dir)
                prefix = []
                r = root
                while r != package_dir:
                    r, dir = os.path.split(r)
                    prefix.insert(0, dir)
                    assert r.startswith(package_dir)
                if prefix:
                    prefix = os.path.join(*prefix)
                for file in files:
                    for ext in ALLOWED_EXTENSIONS:
                        if file.endswith('.%s' % ext) and not file.startswith('.'):
                            break
                    else:
                        continue
                    if prefix:
                        file = os.path.join(prefix, file)
                    package_data[package].append(file)
            break

# Setup SchoolTool
setup(
    name="schooltool",
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

Any modern web browser is suitable for the web application interface.  The
interface degrades gracefully, so a browser that does not support CSS or
Javascript will be usable, although perhaps not very nice or convenient.""",
    version=get_version(),
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
    package_dir={'': 'src'},
    packages=package_data.keys(),
    install_requires=['pytz',
                      'zc.resourcelibrary >= 0.7dev_r72506',
                      'zc.table >= 0.7dev_r72459', 'zc.catalog >= 1.2dev',
                      'hurry.query >= 0.9.2',
                      'zc.datetimewidget >= 0.6.1dev_r72453',
                      'zope.ucol >= 1.0.2', 'zope.html == 0.1dev_r72429',
                      'zope.file >= 0.1dev_r72428',
                      'zope.mimetype >= 1.1dev_r72462',
                      'zope.i18nmessageid',
                      'zope.app.catalog',
                      'zope.viewlet',
                      'zope.app.file',
                      'zope.app.onlinehelp',
                      'zope.app.apidoc',
                      'z3c.breadcrumb',
                      'z3c.layer',
                      'z3c.menu',
                      'z3c.optionstorage',
                      'z3c.pagelet',
                      'z3c.template',
                      'z3c.viewlet',
                      'zope.wfmc',
                      'zope.app.wfmc',
                      'zope.server',
                      'zope.app.wsgi',
                      'zope.app.server',
                      'zope.app.generations',
                      'zope.app.securitypolicy',
                      'zope.app.zcmlfiles',
                      'PasteDeploy',
                      'PasteScript',
                      'zope.paste',
                      'WSGIUtils'],
    dependency_links=['http://ftp.schooltool.org/schooltool/eggs/',
                      'http://download.zope.org/distribution/'],
    entry_points = """
    [paste.app_factory]
    main = schooltool.paste.main:schooltool_app_factory

    [console_scripts]
    make-schooltool-instance = schooltool.paste.instance:make_schooltool_instance

    [paste.paster_create_template]
    schooltool_deploy = schooltool.paste.templates:SchoolToolDeploy
    """,
    package_data=package_data,
    include_package_data=True
    )
