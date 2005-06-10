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
Main SchoolTool script.

This module is not necessary if you use SchoolTool as a Zope 3 content object.
It is only used by the standalone SchoolTool executable.

$Id$
"""

import locale
import gettext
import os.path

from schoolbell.app.main import StandaloneServer as SchoolBellServer
from schoolbell.app.main import Options as SchoolBellOptions

from schooltool.app import SchoolToolApplication, Person
from schooltool.interfaces import ISchoolToolApplication


locale_charset = locale.getpreferredencoding()

localedir = os.path.join(os.path.dirname(__file__), 'locales')
catalog = gettext.translation('schooltool', localedir, fallback=True)
_ = lambda us: catalog.ugettext(us).encode(locale_charset, 'replace')


st_incompatible_db_error_msg = _("""
This is not a SchoolTool 0.10 database file, aborting.
""").strip()


st_old_db_error_msg = _("""
This is not a SchoolTool 0.10 database file, aborting.

Please run the standalone database upgrade script.
""").strip()


class Options(SchoolBellOptions):
    config_filename = 'schooltool.conf'


SCHOOLTOOL_SITE_DEFINITION = u"""\
<?xml version="1.0" encoding="utf-8"?>
<configure xmlns="http://namespaces.zope.org/zope"
           xmlns:browser="http://namespaces.zope.org/browser">

  <include package="zope.app" />
  <include package="zope.app.securitypolicy" file="meta.zcml" />

  <include package="zope.app.session" />
  <include package="zope.app.server" />
  <include package="zope.app.http" />

  <!-- Workaround to shut down a DeprecationWarning that appears because we do
       not include zope.app.onlinehelp and the rotterdam skin tries to look for
       this menu -->
  <browser:menu id="help_actions" />

  <include package="schoolbell.app" />
  <include package="schooltool" />

  <include package="zope.app.securitypolicy" file="securitypolicy.zcml" />

  <unauthenticatedPrincipal id="zope.anybody" title="%(unauth_user)s" />
  <unauthenticatedGroup id="zope.Anybody" title="%(unauth_users)s" />
  <authenticatedGroup id="zope.Authenticated" title="%(auth_users)s" />
  <everybodyGroup id="zope.Everybody" title="%(all_users)s" />

</configure>
""" % {'unauth_user': catalog.ugettext("Unauthenticated User"),
       'unauth_users': catalog.ugettext("Unauthenticated Users"),
       'auth_users': catalog.ugettext("Authenticated Users"),
       'all_users': catalog.ugettext("All Users")}

# Mark strings for i18n extractor
_("Unauthenticated User"), _("Unauthenticated Users")
_("Authenticated Users"), _("All Users")

SCHOOLTOOL_SITE_DEFINITION = SCHOOLTOOL_SITE_DEFINITION.encode('utf-8')


class StandaloneServer(SchoolBellServer):

    incompatible_db_error_msg = st_incompatible_db_error_msg
    old_db_error_msg = st_old_db_error_msg
    Options = Options
    Person = Person
    system_name = 'SchoolTool'
    AppFactory = SchoolToolApplication
    AppInterface = ISchoolToolApplication
    SITE_DEFINITION = SCHOOLTOOL_SITE_DEFINITION


if __name__ == '__main__':
    StandaloneServer().main()
