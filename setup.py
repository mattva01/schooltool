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


# Check python version
import sys
if sys.version_info < (2, 4):
    print >> sys.stderr, '%s: need Python 2.4 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)

import site
site.addsitedir('eggs')

import pkg_resources
pkg_resources.require("setuptools>=0.6a11")

import os
from setuptools import setup, find_packages

def get_version():
    version_file = os.path.join('src', 'schooltool', 'version.txt')
    f = open(version_file, 'r')
    result = f.read()
    f.close()
    return result

# Define packages we want to recursively include, we do this explicitly here
# to avoid automatic accidents
root_packages = ['schooltool.app',
                 'schooltool.dashboard',
                 'schooltool.demographics',
                 'schooltool.generations',
                 'schooltool.securitypolicy',
                 'schooltool.relationship',
                 'schooltool.course',
                 'schooltool.timetable',
                 'schooltool.person',
                 'schooltool.help',
                 'schooltool.locales',
                 'schooltool.locales.en',
                 'schooltool.resource',
                 'schooltool.utility',
                 'schooltool.term',
                 'schooltool.table',
                 'schooltool.group',
                 'schooltool.widget',
                 'schooltool.attendance',
                 'schooltool.calendar',
                 'schooltool.skin',
                 'schooltool.tests',
                 'schooltool.testing',
                 'schooltool.traverser',

                 # only needed for tests
                 'schooltool.sampledata',
                 'schooltool.gradebook',
                 'schooltool.requirement',
                 'schooltool.level',
                 ]

# Packages we want to non-recursively include
packages = ['schooltool']

package_data = {'schooltool': ['*.zcml', 'version.txt']}

# filter packages eliminating things that don't match
all_packages = set(find_packages('src'))
for package in all_packages:
    for root_package in root_packages:
        if package.startswith(root_package):
            packages.append(package)
            package_data[package] = ['*.zcml',
                                     '*.xml',
                                     '*.xpdl',
                                     '*.txt', # only for tests
                                     '*.conf', # only for tests
                                     '*/*.ics', # only for tests
                                     '*.pt', '*/*.pt',
                                     '*/*.png',
                                     '*.css', '*/*.css',
                                     '*/*/*.css',
                                     '*/*.js',
                                     '*/*/*.js',
                                     '*/*.ico',
                                     '*/*.gif',
                                     '*/*/*.gif']
            break

package_data['schooltool.locales'].append('*/*/*.po')

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
    packages=packages,
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
                      'z3c.optionstorage',
                      'zope.wfmc',
                      'zope.app.wfmc',
                      'zope.server',
                      'zope.app.wsgi',
                      'zope.app.server',
                      'zope.app.generations',
                      'zope.app.securitypolicy',
                      'zope.app.zcmlfiles'],
    dependency_links=['http://ftp.schooltool.org/schooltool/eggs/',
                      'http://download.zope.org/distribution/'],
    package_data=package_data
    )
