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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
SchoolBell Testing Support

$Id: app.py 4705 2005-08-15 14:49:07Z srichter $
"""
__docformat__ = 'restructuredtext'
from schooltool.app.security import setUpLocalAuth
from schooltool.testing import registry

# ----------------------------- Session setup ------------------------------
from zope.publisher.interfaces import IRequest
from zope.app.session.http import CookieClientIdManager
from zope.app.session.interfaces import ISessionDataContainer
from zope.app.session.interfaces import IClientId
from zope.app.session.interfaces import IClientIdManager, ISession
from zope.app.session.session import ClientId, Session
from zope.app.session.session import PersistentSessionDataContainer
from zope.app.testing import ztapi
def setupSessions():
    """Set up the session machinery.

    Do this after placelessSetUp().
    """
    ztapi.provideAdapter(IRequest, IClientId, ClientId)
    ztapi.provideAdapter(IRequest, ISession, Session)
    ztapi.provideUtility(IClientIdManager, CookieClientIdManager())
    sdc = PersistentSessionDataContainer()
    ztapi.provideUtility(ISessionDataContainer, sdc)


# --------------------- Local Permission Manager Setup ---------------------
from zope.app.annotation.interfaces import IAnnotatable
from zope.app.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.app.securitypolicy.principalpermission import \
     AnnotationPrincipalPermissionManager
from zope.app.testing import setup
def setupLocalGrants():
    """Set up annotations and AnnotatationPrincipalPermissionManager"""
    setup.setUpAnnotations()
    setup.setUpTraversal()
    ztapi.provideAdapter(IAnnotatable, IPrincipalPermissionManager,
                         AnnotationPrincipalPermissionManager)


# --------------------- Create a SchoolBell application --------------------
from schooltool.app.app import SchoolToolApplication
def createSchoolToolApplication():
    """Create a ``SchoolToolApplication`` instance with all its high-level
    containers."""
    app = SchoolToolApplication()
    registry.setupApplicationContainers(app)
    return app


# ----------------- Setup SchoolBell application as a site -----------------
from zope.interface import directlyProvides
from zope.app.component.hooks import setSite
from zope.app.component.site import LocalSiteManager
from zope.app.traversing.interfaces import IContainmentRoot
def setupSchoolToolSite():
    """This should only be called after ``placefulSetUp()``."""
    app = createSchoolToolApplication()
    directlyProvides(app, IContainmentRoot)
    app.setSiteManager(LocalSiteManager(app))
    setUpLocalAuth(app)
    setSite(app)
    return app

# --------------- Setup Calendar Adapter and set IHaveCalendar -------------
from schooltool.app.interfaces import IHaveCalendar
from schooltool.app.interfaces import ISchoolToolCalendar
from schooltool.app.cal import getCalendar
def setupCalendaring():
    ztapi.provideAdapter(IHaveCalendar, ISchoolToolCalendar, getCalendar)
    registry.setupCalendarComponents()


# ----------------- Setup SchoolTool application preferences ---------------
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.app import getApplicationPreferences
def setUpApplicationPreferences():
    """A utility method for setting up the ApplicationPreferences adapter."""
    ztapi.provideAdapter(ISchoolToolApplication, IApplicationPreferences,
                         getApplicationPreferences)
