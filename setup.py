#!/usr/bin/env python
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008    Shuttleworth Foundation,
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

import sys
from setuptools import setup, find_packages
from distutils import log
from distutils.util import newer
from distutils.spawn import find_executable

# allowed extensions
ALLOWED_EXTENSIONS = ['conf','css', 'gif', 'ico', 'ics', 'js', 'po', 'pt',
                      'png', 'txt', 'xml', 'xpdl', 'zcml']

# Define packages we want to recursively include, we do this explicitly here
# to avoid automatic accidents
root_packages = ['schooltool.app',
                 'schooltool.attendance',
                 'schooltool.basicperson',
                 'schooltool.calendar',
                 'schooltool.course',
                 'schooltool.dashboard',
                 'schooltool.devmode',
                 'schooltool.demographics',
                 'schooltool.email',
                 'schooltool.export',
                 'schooltool.generations',
                 'schooltool.group',
                 'schooltool.help',
                 'schooltool.locales',
                 'schooltool.note',
                 'schooltool.paste',
                 'schooltool.person',
                 'schooltool.resource',
                 'schooltool.relationship',
                 'schooltool.securitypolicy',
                 'schooltool.setupdata',
                 'schooltool.skin',
                 'schooltool.table',
                 'schooltool.contact',
                 'schooltool.term',
                 'schooltool.tests',
                 'schooltool.testing',
                 'schooltool.timetable',
                 'schooltool.traverser',
                 'schooltool.utility',
                 'schooltool.widget',
                 'schooltool.common',
                 'schooltool.schoolyear',

                 # The schooltool configurations we maintain
                 'schooltool.stapp2005',
                 'schooltool.stapp2007',

                 # only needed for tests
                 'schooltool.sampledata',
                 'schooltool.level',
                 ]

from glob import glob

def compile_translations(domain):
    "Compile *.po files to *.mo files"
    locales_dir = 'src/%s/locales' % (domain.replace('.', '/'))
    for po in glob('%s/*.po' % locales_dir):
        lang = os.path.basename(po)[:-3]
        mo = "%s/%s/LC_MESSAGES/%s.mo" % (locales_dir, lang, domain)
        if newer(po, mo):
            log.info('Compile: %s -> %s' % (po, mo))
            messages_dir = os.path.dirname(mo)
            if not os.path.isdir(messages_dir):
                os.makedirs(messages_dir)
            os.system('msgfmt -o %s %s' % (mo, po))

if len(sys.argv) > 1 and sys.argv[1] in ('build', 'install'):
    if not find_executable('msgfmt'):
        log.warn("GNU gettext msgfmt utility not found!")
        log.warn("Skip compiling po files.")
    else:
        compile_translations('schooltool')
        compile_translations('schooltool.commendation')

if len(sys.argv) > 1 and sys.argv[1] == 'clean':
    for mo in glob('src/schooltool/locales/*/LC_MESSAGES/*.mo'):
        os.unlink(mo)
        os.removedirs(os.path.dirname(mo))
    for mo in glob('src/schooltool/commendation/locales/*/LC_MESSAGES/*.mo'):
        os.unlink(mo)
        os.removedirs(os.path.dirname(mo))

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
            package_dir = os.path.join(here, 'src', *package.split('.'))
            for root, dirs, files in os.walk(package_dir):
                prefix = root[len(package_dir)+1:]
                for file in files:
                    name, ext = os.path.splitext(file)
                    if (ext[1:] in ALLOWED_EXTENSIONS
                        and not file.startswith('.')):
                        file = os.path.join(prefix, file)
                        package_data[package].append(file)
            break

if os.path.exists("version.txt"):
    version = open("version.txt").read().strip()
else:
    version = open("version.txt.in").read().strip()

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
    version=version,
    url='http://www.schooltool.org',
    license="GPL",
    maintainer="SchoolTool Developers",
    maintainer_email="schooltool-developers@lists.launchpad.net",
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
    namespace_packages=["schooltool"],
    packages=package_data.keys(),
    install_requires=['pytz',
                      'zc.resourcelibrary',
                      'zc.table',
                      'zc.catalog',
                      'hurry.query',
                      'zc.datetimewidget',
                      'zope.component<3.6.0',
                      'zope.ucol',
                      'zope.html',
                      'zope.file',
                      'zope.mimetype',
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
                      'zope.securitypolicy',
                      'zope.app.traversing',
                      'zope.app.securitypolicy',
                      'zope.app.zcmlfiles',
                      'zope.app.session',
                      'zope.session',
                      'rwproperty',
                      'z3c.form',
                      'z3c.formui',
                      'z3c.rml',
                      'lxml',
                      'PILwoTk',
                      'Reportlab',
                      'PasteDeploy',
                      'PasteScript',
                      'xlwt',
                      'xlrd',
                      'setuptools'],
    tests_require=['zope.testing',
                   'schooltool.lyceum.journal'],
    dependency_links=['http://ftp.schooltool.org/schooltool/1.2/'],
    entry_points = """
    [paste.app_factory]
    main = schooltool.paste.main:schooltool_app_factory

    [console_scripts]
    start-schooltool-instance = schooltool.paste.run:main
    make-schooltool-instance = schooltool.paste.instance:make_schooltool_instance

    [paste.paster_create_template]
    schooltool_deploy = schooltool.paste.templates:SchoolToolDeploy

    [schooltool.instance_type]
    stapp2005 = schooltool.stapp2005
    stapp2007 = schooltool.stapp2007

    """,
    package_data=package_data,
    include_package_data=True
    )
