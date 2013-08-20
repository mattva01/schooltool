#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
School year testing related code
"""
from zope.app.testing.functional import FunctionalTestSetup
from zope.component.hooks import getSite, setSite


def provideStubAdapter(factory, adapts=None, provides=None, name=u''):
    sm = getSite().getSiteManager()
    sm.registerAdapter(factory, required=adapts, provided=provides, name=name)


def provideStubUtility(component, provides=None, name=u''):
    sm = getSite().getSiteManager()
    sm.registerUtility(component, provided=provides, name=name)


def setUp(test):
    fts = FunctionalTestSetup()
    fts.setUp()
    app = fts.getRootFolder()
    setSite(app)


def tearDown(test):
    setSite(None)
    fts = FunctionalTestSetup()
    fts.tearDown()
