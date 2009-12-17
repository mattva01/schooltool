#!/usr/bin/env python
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008, 2009 Shuttleworth Foundation,
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

import sys
import os
from setuptools import setup, find_packages
from distutils import log
from distutils.util import newer
from distutils.spawn import find_executable

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

if os.path.exists("version.txt"):
    version = open("version.txt").read().strip()
else:
    version = open("version.txt.in").read().strip()

setup(
    name="schooltool",
    description="A common information systems platform for school administration.",
    long_description="""
SchoolTool is an open source school management information system.  It is
a web application, usable with an ordinary browser.

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
    packages=find_packages('src'),
    namespace_packages=["schooltool"],
    install_requires=['pytz',
                      'zc.resourcelibrary',
                      'zc.table',
                      'zc.catalog',
                      'hurry.query',
                      'zc.datetimewidget',
                      'zope.component',
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
                      'z3c.autoinclude',
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
    tests_require=['zope.testing'],
    dependency_links=['http://ftp.schooltool.org/schooltool/1.2/'],
    include_package_data=True,
    zip_safe=False,
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
    schooltool = schooltool.stapp2007

    """,
    )
