#!/usr/bin/env python
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003-2013 Shuttleworth Foundation
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
"""
SchoolTool setup script.
"""

import os
from setuptools import setup, find_packages

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
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Zope",
    "Topic :: Education"],
    package_dir={'': 'src'},
    packages=find_packages('src'),
    namespace_packages=["schooltool"],
    install_requires=['celery>=2.5',
                      'redis',
                      'bottle',
                      'PasteDeploy',
                      'PasteScript',
                      'Pillow',
                      'pytz',
                      'reportlab',
                      'setuptools',
                      'xlrd',
                      'xlwt',
                      'z3c.autoinclude',
                      'z3c.form>=2.0',
                      'z3c.formui',
                      'z3c.macro',
                      'z3c.rml',
                      'z3c.template',
                      'zc.catalog',
                      'zc.datetimewidget',
                      'zc.resourcelibrary',
                      'zc.table',
                      'ZODB3',
                      'zope.annotation',
                      'zope.authentication',
                      'zope.app.applicationcontrol',
                      'zope.app.appsetup',
                      'zope.app.basicskin',
                      'zope.app.broken',
                      'zope.app.component',
                      'zope.app.container',
                      'zope.app.dependable',
                      'zope.app.error',
                      'zope.app.exception',
                      'zope.app.form',
                      'zope.app.generations>=3.5',
                      'zope.app.http',
                      'zope.app.locales',
                      'zope.app.principalannotation',
                      'zope.app.publication',
                      'zope.app.schema',
                      'zope.app.security',
                      'zope.app.wsgi',
                      'zope.browser',
                      'zope.browsermenu',
                      'zope.browserpage>=3.10.1',
                      'zope.cachedescriptors',
                      'zope.catalog',
                      'zope.component>=3.8',
                      'zope.configuration',
                      'zope.container>=3.7.2',
                      'zope.contentprovider',
                      'zope.dublincore>=3.7',
                      'zope.event',
                      'zope.file',
                      'zope.filerepresentation',
                      'zope.formlib>=4.0',
                      'zope.html',
                      'zope.i18n>=3.5',
                      'zope.i18nmessageid',
                      'zope.interface',
                      'zope.intid',
                      'zope.keyreference',
                      'zope.lifecycleevent',
                      'zope.location',
                      'zope.login',
                      'zope.mimetype',
                      'zope.pagetemplate>=3.5',
                      'zope.password',
                      'zope.proxy',
                      'zope.publisher>=3.6',
                      'zope.schema',
                      'zope.security',
                      'zope.securitypolicy',
                      'zope.server',
                      'zope.session',
                      'zope.site',
                      'zope.size',
                      'zope.tales',
                      'zope.testing',
                      'zope.testbrowser',   # XXX for selenium extensions
                      'zope.app.testing',   # XXX to get zope.testbrowser.testing.Browser
                      'zope.traversing>=3.13',
                      'zope.ucol',
                      'zope.viewlet'],
    extras_require={'test': ['lxml',
                             'zope.app.testing',
                             'zope.copypastemove',
                             'zope.exceptions',
                             'zope.principalregistry',
                             'zope.testbrowser',
                             'z3c.form>=2.6',
                             'schooltool.devtools>=0.7.1',
                             'selenium'],
                    'docs': ['Sphinx',
                             'z3c.recipe.sphinxdoc'],
                   },
    include_package_data=True,
    zip_safe=False,
    entry_points = """
    [paste.app_factory]
    main = schooltool.paste.main:schooltool_app_factory
    task_results = schooltool.paste.main:task_result_app_factory

    [console_scripts]
    start-schooltool-instance = schooltool.paste.run:main
    make-schooltool-instance = schooltool.paste.instance:make_schooltool_instance
    schooltool-server = schooltool.app.main:main

    [paste.paster_create_template]
    schooltool_deploy = schooltool.paste.templates:SchoolToolDeploy

    [schooltool.instance_type]
    old = schooltool.standard
    schooltool = schooltool.skin.flourish.instance

    """,
    )
