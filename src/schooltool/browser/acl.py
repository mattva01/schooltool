#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Browser views for ACLs.

$Id$
"""

from schooltool.browser import View, Template
from schooltool.browser.auth import PrivateAccess
from schooltool.component import traverse, getPath, traverse
from schooltool.translation import ugettext as _
from schooltool.interfaces import Everybody, ViewPermission
from schooltool.interfaces import AddPermission, ModifyPermission
from schooltool.interfaces import IPerson, IGroup
from schooltool.browser.widgets import SelectionWidget
from schooltool.browser import absoluteURL

__metaclass__ = type


class ACLView(View):
    """Calendar access list view."""

    authorization = PrivateAccess

    template = Template("www/acl.pt")

    def __init__(self, context):
        View.__init__(self, context)

        # XXX "principal" is heavy Zope 3 jargon that is guaranteed to be
        # misunderstood in school contexts.  Rename it to "user"

        self.principal_widget = SelectionWidget(
            'principal', _('Principal'),
            [(None, _('Select principal')), (Everybody, _('Everybody'))] +
            [(obj, obj.title) for obj in self.allPrincipals()],
            parser=self.principalParser,
            formatter=self.formatPrincipal,
            validator=self.principalValidator)

        self.permission_widget = SelectionWidget(
            'permission', _('Permission'),
            [(None, _('Select permission'))] +
            [(ViewPermission, _('View')),
             (AddPermission, _('Add')),
             (ModifyPermission, _('Modify'))],
            validator=self.permissionValidator,
            formatter=self.formatPermission
            )

    def principalParser(self, value):
        if value in (None, ''):
            return value
        elif value == Everybody:
            return Everybody
        try:
           return traverse(self.context, value)
        except TypeError:
           return None

    def formatPrincipal(self, value):
        if value in ('', None):
            return ''
        elif value == Everybody:
            return Everybody
        else:
            return getPath(value)

    def formatPermission(self,  value):
        if not value:
            return ''
        return value

    def principalValidator(self, value):
        if (not IPerson.providedBy(value) and not IGroup.providedBy(value) and
            value is not None and value != Everybody):
            raise ValueError(_("Please select a principal"))

    def permissionValidator(self, value):
        if value not in (ViewPermission, AddPermission, ModifyPermission, None):
            raise ValueError(_("Please select a permission"))

    def list(self):
        """List all grants."""
        grants = []
        for user, permission in self.context:
            if user == Everybody:
                stone = 1 # make it heavy so it ends up at the bottom
                title = _('Everybody')
                value = '%s:%s' % (permission, user)
                url = None
            else:
                stone = 0
                title = user.title
                value = '%s:%s' % (permission, getPath(user))
                url = absoluteURL(self.request, user)
            # XXX: i18nize the permission name.  The tricky part is to make
            # i18nextractor see the set of allowed values.
            grants.append((stone, title, {'title': title, 'url': url,
                                          'permission': permission,
                                          'value': value}))
        grants.sort()
        return [item for heavy_stone, title, item in grants]

    def allPrincipals(self):
        """Return a list of objects available for addition"""
        result = []

        for path in ('/groups', '/persons'):
            for obj in traverse(self.context, path).itervalues():
                # XXX who uses __class__.__name__ in this way?! *thwap*
                result.append((obj.__class__.__name__, obj.title, obj))
        result.sort()
        return [obj for cls, title, obj in result]

    def update(self):
        result = []
        self.principal_widget.update(self.request)
        self.permission_widget.update(self.request)
        if 'DELETE' in self.request.args:
            for checkbox in self.request.args.get('CHECK', []):
                perm, path = checkbox.split(':', 1)
                if path == Everybody:
                    obj = Everybody
                else:
                    try:
                        obj = traverse(self.context, path)
                    except KeyError:
                        continue
                try:
                    self.context.remove((obj, perm))
                except KeyError:
                    pass
                else:
                    self.request.appLog(
                        _("Revoked permission %s on %s from %s") %
                        (perm, getPath(self.context),
                         self.printPrincipal(obj)))
                    result.append(_("Revoked permission %s from %s") %
                                  (perm, self.printPrincipal(obj)))
            return "; ".join(result)

        if 'ADD' in self.request.args:
            self.permission_widget.require()
            self.principal_widget.require()

            if not (self.principal_widget.error or
                    self.permission_widget.error):
                principal = self.principal_widget.value
                permission = self.permission_widget.value
                if (principal, permission) in self.context:
                    return _("%s already has permission %s") % \
                           (principal.title, permission)
                self.context.add((principal, permission))
                self.request.appLog(
                    _("Granted permission %s on %s to %s") %
                    (permission, getPath(self.context),
                     self.printPrincipal(principal)))
                return _("Granted permission %s to %s") % \
                       (permission, self.printPrincipal(principal))

    def printPrincipal(self, principal):
        if principal == Everybody:
            return Everybody
        else:
            return "%s (%s)" % (getPath(principal), principal.title)
