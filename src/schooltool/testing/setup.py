#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
SchoolTool Testing Support
"""
__docformat__ = 'restructuredtext'
from schooltool.app.security import setUpLocalAuth
from schooltool.testing import registry

# ----------------------------- Session setup ------------------------------
from zope.publisher.interfaces import IRequest
from zope.component import provideAdapter, provideUtility
from zope.session.http import CookieClientIdManager
from zope.session.interfaces import ISessionDataContainer
from zope.session.interfaces import IClientIdManager, ISession
from zope.session.session import ClientId, Session
from zope.session.session import PersistentSessionDataContainer
def setUpSessions():
    """Set up the session machinery.

    Do this after placelessSetUp().
    """
    provideAdapter(ClientId)
    provideAdapter(Session, (IRequest,), ISession)
    provideUtility(CookieClientIdManager(), IClientIdManager)
    sdc = PersistentSessionDataContainer()
    provideUtility(sdc, ISessionDataContainer)


# --------------------- Create a SchoolTool application --------------------
from schooltool.app.app import SchoolToolApplication
def createSchoolToolApplication():
    """Create a ``SchoolToolApplication`` instance with all its high-level
    containers."""
    app = SchoolToolApplication()
    registry.setupApplicationContainers(app)
    return app


# ----------------- Setup SchoolTool application as a site -----------------
from zope.interface import Interface
from zope.interface import directlyProvides
from zope.component.hooks import setSite
from zope.site import LocalSiteManager
from zope.traversing.interfaces import IContainmentRoot
from schooltool.app.app import getSchoolToolApplication
from schooltool.app.security import PersonContainerAuthenticationPlugin
def setUpSchoolToolSite():
    """This should only be called after ``placefulSetUp()``."""
    app = createSchoolToolApplication()
    directlyProvides(app, IContainmentRoot)
    app.setSiteManager(LocalSiteManager(app))
    setUpLocalAuth(app)

    plugin = PersonContainerAuthenticationPlugin()
    provideUtility(plugin)
    provideAdapter(getSchoolToolApplication, (Interface,), ISchoolToolApplication)

    from schooltool.app.catalog import getAppCatalogs
    getAppCatalogs(app)
    from schooltool.relationship.catalog import URICacheStartUp
    URICacheStartUp(app)()

    setSite(app)
    return app

# --------------- Setup Calendar Adapter and set IHaveCalendar -------------
from schooltool.app.interfaces import IHaveCalendar
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.cal import getCalendar
from schooltool.app.browser.cal import getCalendarEventDeleteLink
def setUpCalendaring():
    provideAdapter(getCalendar, (IHaveCalendar,), ISchoolToolCalendar)
    provideAdapter(getCalendarEventDeleteLink, name="delete_link")
    registry.setupCalendarComponents()


# ----------------- Setup SchoolTool application preferences ---------------
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.app import getApplicationPreferences
def setUpApplicationPreferences():
    """A utility method for setting up the ApplicationPreferences adapter."""
    provideAdapter(getApplicationPreferences,
                   (ISchoolToolApplication,), IApplicationPreferences)


# --------------------------------------------------------------------------
_import_chickens = {}, {}, ("*",) # dead chickens needed by __import__
from zope.configuration import xmlconfig

class ZCMLWrapper(object):
    """Wrapper for more convenient zcml execution."""
    auto_execute = True
    context = None
    namespaces = None
    i18n_domain = ''

    def __init__(self, context=None):
        self.context = context
        self.namespaces = {}

    def setUp(self, namespaces={}, i18n_domain=""):
        """Set active namespaces and translation domain.

           namespaces = {
               '': "http://namespaces.zope.org/zope",
               'meta': "http://namespaces.zope.org/meta"
               }
           i18ndomain = 'foo'

        Will wrap ZCML passed to string() with:

            <configure
                xmlns="http://namespaces.zope.org/zope"
                xmlns:meta="http://namespaces.zope.org/meta"
                i18ndomain="foo">
            ...
            </configure>

        """
        self.namespaces = namespaces.copy()
        self.i18n_domain = i18n_domain

    def string(self, string, name="<string>"):
        config = ''
        if self.namespaces:
            config = ' ' + ' '.join(
                ['xmlns%s="%s"' % (short and ':' + short, long)
                 for short, long in sorted(self.namespaces.items())])
        if self.i18n_domain:
            config += ' i18n_domain="%s"' % self.i18n_domain

        string = '<configure%s>\n' % config + string + '\n</configure>'

        self.context = xmlconfig.string(
            string, context=self.context, name=name,
            execute=self.auto_execute)

    def include(self, package=None, file='configure.zcml'):
        if isinstance(package, str):
            package = __import__(package, *_import_chickens)
        self.context = xmlconfig.file(
            file, package=package, context=self.context,
            execute=self.auto_execute)

    def execute(self):
        if self.context is not None:
            self.context.execute_actions()
