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
Main SchoolBell script.

This module is not necessary if you use SchoolBell as a Zope 3 content object.
It is only used by the standalone SchoolBell executable.

$Id$
"""
import locale
import gettext
import os.path
from schooltool.app import main

locale_charset = locale.getpreferredencoding()

localedir = os.path.join(os.path.dirname(__file__), 'locales')
catalog = gettext.translation('schoolbell', localedir, fallback=True)
_ = lambda us: catalog.ugettext(us).encode(locale_charset, 'replace')

sb_incompatible_db_error_msg = _("""
This is not a SchoolBell 1.0 database file, aborting.
""").strip()


sb_old_db_error_msg = _("""
This is not a SchoolBell 1.0 database file, aborting.

Please run the standalone database upgrade script.
""").strip()


class Options(main.options):
    """SchoolBell process options."""

    config_filename = 'schoolbell.conf'


SCHOOLBELL_SITE_DEFINITION = """\
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

  <include package="zope.app.securitypolicy"/>

  <!-- Basically a copy of zope.app.securitypolicy/securitypolicy.zcml  -->
  <securityPolicy
    component="zope.app.securitypolicy.zopepolicy.ZopeSecurityPolicy" />

  <role id="zope.Anonymous" title="Everybody"
                 description="All users have this role implicitly" />
  <role id="zope.Manager" title="Site Manager" />
  <role id="zope.Member" title="Site Member" />

  <grant permission="zope.View" role="zope.Anonymous" />
  <grant permission="zope.app.dublincore.view" role="zope.Anonymous" />

  <grantAll role="zope.Manager" />

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

SCHOOLBELL_SITE_DEFINITION = SCHOOLBELL_SITE_DEFINITION.encode('utf-8')


class StandaloneServer(main.StandaloneServer):

    SITE_DEFINITION = SCHOOLBELL_SITE_DEFINITION

    incompatible_db_error_msg = sb_incompatible_db_error_msg
    old_db_error_msg = sb_old_db_error_msg

    system_name = "SchoolBell"

    Options = Options


if __name__ == '__main__':
    StandaloneServer().main()
