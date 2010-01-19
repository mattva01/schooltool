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
    install_requires=['hurry.query',
                      'PasteDeploy',
                      'PasteScript',
                      'PILwoTk',
                      'pytz',
                      'Reportlab',
                      'rwproperty',
                      'setuptools',
                      'xlrd',
                      'xlwt',
                      'z3c.autoinclude',
                      'z3c.form',
                      'z3c.formui',
                      'z3c.macro',
                      'z3c.rml',
                      'z3c.template',
                      'zc.catalog',
                      'zc.datetimewidget',
                      'zc.resourcelibrary',
                      'zc.table',
                      'zope.annotation',
                      'zope.app.apidoc',
                      'zope.app.applicationcontrol',
                      'zope.app.appsetup',
                      'zope.app.basicskin',
                      'zope.app.catalog', # BBB
                      'zope.app.dependable',
                      'zope.app.exception',
                      'zope.app.file',
                      'zope.app.form',
                      'zope.app.generations',
                      'zope.app.http',
                      'zope.app.intid', # BBB
                      'zope.app.onlinehelp',
                      'zope.app.pagetemplate',
                      'zope.app.publication',
                      'zope.app.security',
                      'zope.app.server',
                      'zope.app.session',
                      'zope.app.tree',
                      'zope.app.wsgi',
                      'zope.app.zcmlfiles',
                      'zope.browser',
                      'zope.browsermenu',
                      'zope.cachedescriptors',
                      'zope.component>=3.6.0',
                      'zope.configuration',
                      'zope.container>=3.7.2',
                      'zope.contentprovider',
                      'zope.event',
                      'zope.file',
                      'zope.filerepresentation',
                      'zope.formlib',
                      'zope.html',
                      'zope.i18n',
                      'zope.i18nmessageid',
                      'zope.interface',
                      'zope.keyreference',
                      'zope.lifecycleevent',
                      'zope.location',
                      'zope.mimetype',
                      'zope.pagetemplate',
                      'zope.password',
                      'zope.proxy',
                      'zope.publisher>=3.6.0',
                      'zope.schema',
                      'zope.security',
                      'zope.securitypolicy',
                      'zope.server',
                      'zope.session',
                      'zope.site',
                      'zope.size',
                      'zope.tales',
                      'zope.testing',
                      'zope.traversing',
                      'zope.ucol',
                      'zope.viewlet'],
    extras_require={'test': ['lxml',
                             'zope.app.testing',
                             'zope.copypastemove',
                             'zope.exceptions',
                             'zope.testbrowser']},
    dependency_links=['http://ftp.schooltool.org/schooltool/1.4/'],
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
